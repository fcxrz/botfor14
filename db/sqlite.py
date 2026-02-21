import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file="bridge_db.sqlite"):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # юзеры
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (user_id INTEGER PRIMARY KEY, role TEXT)''')
        
        # капсулы (поф они просто есть пока что)
        cursor.execute('''CREATE TABLE IF NOT EXISTS capsules 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           user_id INTEGER, 
                           file_id TEXT, 
                           context TEXT, 
                           unlock_at DATETIME, 
                           is_viewed INTEGER DEFAULT 0)''')
        
        # логи
        cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                          (id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, timestamp TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS mediation_history 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id INTEGER, 
                   role TEXT, 
                   content TEXT, 
                   timestamp DATETIME)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS hellsing_messages 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   sender_id INTEGER, 
                   recipient_id INTEGER, 
                   from_chat_id INTEGER,
                   message_id INTEGER, 
                   send_at DATETIME, 
                   is_sent INTEGER DEFAULT 0)''')
        
        self.conn.commit()

    

    def set_user(self, user_id, role):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, role))
        self.conn.commit()

    # метод для сохранения и получения истории
    def add_mediation_msg(self, user_id, role, content):
        self.conn.execute("INSERT INTO mediation_history (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                        (user_id, role, content, datetime.now()))
        self.conn.commit()

    def get_mediation_history(self, limit=10):
        return self.conn.execute("SELECT role, content FROM mediation_history ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

    def get_role(self, user_id):
        cursor = self.conn.cursor()
        res = cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return res[0] if res else None

    def save_capsule(self, angel_id, file_id, context, unlock_at):
        query = """
        INSERT INTO capsules (user_id, file_id, context, unlock_at, is_viewed) 
        VALUES (?, ?, ?, ?, 0)
        """
        if isinstance(unlock_at, datetime):
            unlock_at = unlock_at.strftime('%Y-%m-%d %H:%M:%S')
            
        self.conn.execute(query, (angel_id, file_id, context, unlock_at))
        self.conn.commit()

    def get_available_capsules(self):
        # сравнение с текущим временем в формате строки
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = "SELECT id, context, file_id FROM capsules WHERE unlock_at <= ? AND is_viewed = 0"
        return self.conn.execute(query, (now,)).fetchall()
    
    def mark_as_viewed(self, capsule_id):
        self.conn.execute("UPDATE capsules SET is_viewed = 1 WHERE id = ?", (capsule_id,))
        self.conn.commit()

    # метод для сохранения
    def add_hellsing(self, sender_id, recipient_id, chat_id, msg_id, send_at):
        self.conn.execute("INSERT INTO hellsing_messages (sender_id, recipient_id, from_chat_id, message_id, send_at) VALUES (?, ?, ?, ?, ?)",
                        (sender_id, recipient_id, chat_id, msg_id, send_at))
        self.conn.commit()

    def get_pending_hellsings(self):
        cursor = self.conn.execute(
            "SELECT id, recipient_id, from_chat_id, message_id FROM hellsing_messages WHERE send_at <= ? AND is_sent = 0",
            (datetime.now(),)
        )
        return cursor.fetchall()

    def mark_hellsing_sent(self, h_id):
        self.conn.execute(
            "UPDATE hellsing_messages SET is_sent = 1 WHERE id = ?", 
            (h_id,)
        )
        self.conn.commit()