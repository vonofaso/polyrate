import sqlite3
import logging
import json

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER,
                    username TEXT,
                    full_name TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_name TEXT,
                    first_name TEXT,
                    patronymic TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER,
                    score REAL,
                    tags TEXT,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )
            ''')

            logger.info("База данных инициализирована")

    def add_user(self, id: str, username: str, full_name: str):
        """Добавление нового пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, username, full_name)
                VALUES (?, ?, ?)
            ''', (id, username, full_name))
            conn.commit()
            return cursor.lastrowid

    def get_user(self, user_id: int):
        """Получение пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            return cursor.fetchone()

    def add_teacher(self, last_name: str, first_name: str, patronymic: str = None):
        """Добавление преподавателя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO teachers (last_name, first_name, patronymic)
                VALUES (?, ?, ?)
            ''', (last_name, first_name, patronymic))
            conn.commit()
            return cursor.lastrowid

    def get_all_teachers(self):
        """Получение всех преподавателей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM teachers 
                ORDER BY last_name, first_name, patronymic
            ''')
            return cursor.fetchall()

    def get_teacher(self, teacher_id: int):
        """Получение преподавателя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,))
            return cursor.fetchone()

    def get_teacher_full_name(self, teacher_id: int):
        """Получение полного имени преподавателя"""
        teacher = self.get_teacher(teacher_id)
        if teacher:
            parts = [teacher['last_name'], teacher['first_name']]
            if teacher['patronymic']:
                parts.append(teacher['patronymic'])
            return ' '.join(parts)
        return None

    def save_rating(self, teacher_id: int, score: float, tags: list, comment: str = None):
        """Сохранение оценки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ratings (teacher_id, score, tags, comment)
                VALUES (?, ?, ?, ?)
            ''', (teacher_id, score, json.dumps(tags, ensure_ascii=False), comment))
            conn.commit()
            return cursor.lastrowid

    def get_teacher_ratings(self, teacher_id: int):
        """Получение всех оценок преподавателя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ratings 
                WHERE teacher_id = ? 
                ORDER BY created_at DESC
            ''', (teacher_id,))
            return cursor.fetchall()

    def get_teacher_stats(self, teacher_id: int):
        """Получение статистики преподавателя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as rating_count,
                    AVG(score) as avg_score
                FROM ratings 
                WHERE teacher_id = ?
            ''', (teacher_id,))
            return cursor.fetchone()


db = Database("database.db")
