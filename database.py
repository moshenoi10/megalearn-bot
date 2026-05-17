import sqlite3
import json
import os
from datetime import date
from config import ENGLISH_LEVELS, MATH_LEVELS

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            english_level INTEGER DEFAULT 0,
            english_xp INTEGER DEFAULT 0,
            math_level INTEGER DEFAULT 0,
            math_xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT,
            lessons_done INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0,
            total_score_sum INTEGER DEFAULT 0,
            total_quizzes INTEGER DEFAULT 0,
            current_subject TEXT DEFAULT 'none',
            current_topic TEXT DEFAULT '',
            weak_points TEXT DEFAULT '{}',
            conversation_history TEXT DEFAULT '[]',
            awaiting_answer INTEGER DEFAULT 0,
            current_question TEXT DEFAULT '',
            diagnostic_done INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        user = dict(row)
        user['weak_points'] = json.loads(user['weak_points'])
        user['conversation_history'] = json.loads(user['conversation_history'])
        return user
    return None

def create_user(user_id: int, username: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, last_active)
        VALUES (?, ?, ?)
    """, (user_id, username or "user", str(date.today())))
    conn.commit()
    conn.close()
    return get_user(user_id)

def update_user(user_id: int, **kwargs):
    if 'weak_points' in kwargs:
        kwargs['weak_points'] = json.dumps(kwargs['weak_points'])
    if 'conversation_history' in kwargs:
        kwargs['conversation_history'] = json.dumps(kwargs['conversation_history'])
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    c.execute(f"UPDATE users SET {cols} WHERE user_id = ?", vals)
    conn.commit()
    conn.close()

def add_xp(user_id: int, subject: str, amount: int):
    from config import XP_TO_LEVEL_UP
    user = get_user(user_id)
    xp_key = f"{subject}_xp"
    level_key = f"{subject}_level"
    
    new_xp = user[xp_key] + amount
    new_level = user[level_key]
    level_map = ENGLISH_LEVELS if subject == "english" else MATH_LEVELS
    max_level = max(level_map.keys())

    leveled_up = False
    while new_xp >= XP_TO_LEVEL_UP and new_level < max_level:
        new_xp -= XP_TO_LEVEL_UP
        new_level += 1
        leveled_up = True

    update_user(user_id, **{xp_key: new_xp, level_key: new_level})
    return leveled_up, new_level

def record_score(user_id: int, score: int):
    user = get_user(user_id)
    total = user['total_score_sum'] + score
    quizzes = user['total_quizzes'] + 1
    avg = round(total / quizzes)
    update_user(user_id,
        total_score_sum=total,
        total_quizzes=quizzes,
        avg_score=avg,
        lessons_done=user['lessons_done'] + 1
    )

def update_streak(user_id: int):
    user = get_user(user_id)
    today = str(date.today())
    if user['last_active'] != today:
        update_user(user_id, streak=user['streak'] + 1, last_active=today)

def add_weak_point(user_id: int, subject: str, topic: str):
    user = get_user(user_id)
    wp = user['weak_points']
    key = f"{subject}:{topic}"
    wp[key] = wp.get(key, 0) + 1
    update_user(user_id, weak_points=wp)

def reset_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

init_db()
