import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # owners table for vehicle owners
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (plate_number TEXT PRIMARY KEY, name TEXT, role TEXT)''')
    # logging table for entry and exit records
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, plate_number TEXT, 
                       time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT)''')
    
    # Sample data insertion
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('CAS-1234', 'Dr. Perera', 'Lecturer')")
    cursor.execute("INSERT OR IGNORE INTO users VALUES ('BEN-5678', 'Amal Silva', 'Student')")
    
    conn.commit()
    conn.close()

init_db()