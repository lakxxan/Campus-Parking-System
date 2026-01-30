from flask import Flask, render_template, request, jsonify, Response
import cv2
from ultralytics import YOLO
import easyocr
import sqlite3
import os
import re
import numpy as np

app = Flask(__name__)

# --- Setup AI & Camera ---
MODEL_PATH = 'model/best.pt'
model = YOLO(MODEL_PATH)
reader = easyocr.Reader(['en'])
camera = cv2.VideoCapture(0)  # 0 is the default webcam

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Video Streaming Logic ---
def gen_frames():  
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register_vehicle():
    data = request.json
    plate = "".join(re.findall(r'[A-Z0-9]', data.get('plate', '').upper()))
    name = data.get('name', 'Unknown')
    role = data.get('role', 'Visitor')
    
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO users (plate_number, name, role) VALUES (?, ?, ?)", (plate, name, role))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"Registered: {plate}"})
    except:
        return jsonify({"status": "error", "message": "Already registered."})

@app.route('/scan', methods=['POST'])
def scan():
    file = request.files['image']
    img_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    
    # OCR First Strategy with Image Processing
    resized = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    ocr_results = reader.readtext(gray)
    
    raw_text = "".join([res[1].upper() for res in ocr_results])
    plate_text = "".join(re.findall(r'[A-Z0-9]', raw_text))

    # Fallback to YOLO if OCR fails
    if len(plate_text) < 3:
        results = model(img, conf=0.3)
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                crop = img[y1:y2, x1:x2]
                res = reader.readtext(crop)
                if res: plate_text += res[0][1].upper()
        plate_text = "".join(re.findall(r'[A-Z0-9]', plate_text))

    if not plate_text:
        return jsonify({"status": "NOT_FOUND", "plate": "Unknown"})

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE plate_number LIKE ?", (f"%{plate_text}%",)).fetchone()
    conn.close()

    if user:
        return jsonify({"status": "ALLOWED", "plate": plate_text, "name": user['name'], "role": user['role']})
    return jsonify({"status": "DENIED", "plate": plate_text})

@app.route('/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in users])

@app.route('/delete/<plate>', methods=['DELETE'])
def delete_vehicle(plate):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE plate_number = ?", (plate,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Deleted"})

if __name__ == '__main__':
    app.run(debug=True)