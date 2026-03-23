import sqlite3
import os

DB_FILE = 'banking.db'

def init_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        account_number TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        profile_picture TEXT DEFAULT 'default.png',
        balance REAL DEFAULT 0.0,
        cibil_score INTEGER DEFAULT 750
    )
    ''')
    
    # Create Accounts table (For multiple account support if needed)
    cursor.execute('''
    CREATE TABLE accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        account_type TEXT NOT NULL,
        balance REAL DEFAULT 0.0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')
    
    # Create Transactions table
    cursor.execute('''
    CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(sender_id) REFERENCES users(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
