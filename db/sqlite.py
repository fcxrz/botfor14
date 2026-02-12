import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file="bridge_db.sqlite"):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, role TEXT)''')
        # юзеры
        cursor.execute('''CREATE TABLE IF NOT EXISTS capsules 
                          (id INTEGER PRIMARY KEY, file_id BLOB, delivery_date TEXT)''')
        #пасхалко шифровко
        cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                          (id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, timestamp TEXT)''')
        # логи на всякий 
        self.conn.commit()

    def set_user(self, user_id, role):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, role))
        self.conn.commit()

    def get_role(self, user_id):
        cursor = self.conn.cursor()
        res = cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return res[0] if res else None

    def save_capsule(self, file_id_encrypted, days=30):
        date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        self.conn.cursor().execute("INSERT INTO capsules (file_id, delivery_date) VALUES (?, ?)", 
                                   (file_id_encrypted, date))
        self.conn.commit()