import sqlite3
import threading
from config import logger

db_lock = threading.Lock()
DATABASE_FILE = 'user_preferences.db'

def init_database():
    with db_lock:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                prefix TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS probabilities (
                guild_id TEXT,
                channel_id INTEGER,
                reply_probability REAL,
                reaction_probability REAL,
                PRIMARY KEY (guild_id, channel_id)
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database initialized.")

def load_user_prefix(user_id):
    with db_lock:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT prefix FROM user_preferences WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

def save_user_prefix(user_id, prefix):
    with db_lock:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO user_preferences (user_id, prefix) VALUES (?, ?)', (user_id, prefix))
        conn.commit()
        conn.close()

def load_probabilities(guild_id, channel_id):
    with db_lock:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT reply_probability, reaction_probability 
            FROM probabilities 
            WHERE guild_id = ? AND channel_id = ?
            ''',
            (str(guild_id), channel_id)
        )
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0], result[1]
        else:
            return 0.1, 0.1  # Default probabilities (10%)

def save_probabilities(guild_id, channel_id, reply_probability, reaction_probability):
    with db_lock:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            '''
            REPLACE INTO probabilities 
            (guild_id, channel_id, reply_probability, reaction_probability) 
            VALUES (?, ?, ?, ?)
            ''',
            (str(guild_id), channel_id, reply_probability, reaction_probability)
        )
        conn.commit()
        conn.close()