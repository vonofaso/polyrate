import sqlite3
import logging
import json
import csv
import io
import re

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

            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER,
                    username TEXT,
                    full_name TEXT
                )
            ''')

            # Таблица преподавателей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_name TEXT,
                    first_name TEXT,
                    patronymic TEXT
                )
            ''')

            # Таблица оценок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    teacher_id INTEGER,
                    score REAL,
                    tags TEXT,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    moderated INTEGER DEFAULT 1,
                    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
                )
            ''')

            # Таблица жалоб
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_id INTEGER,
                    reporter_id INTEGER,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (review_id) REFERENCES ratings (id)
                )
            ''')

            # Таблица запрещенных слов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS banned_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE
                )
            ''')

            # Таблица настроек модерации
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderation_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Таблица тегов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            ''')

            # Таблица вопросов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    key TEXT UNIQUE NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Вставляем настройки по умолчанию
            cursor.execute("INSERT OR IGNORE INTO moderation_settings (key, value) VALUES ('report_interval', 'daily')")

            # Вставляем базовый список запрещенных слов, если таблица пуста
            cursor.execute("SELECT COUNT(*) FROM banned_words")
            if cursor.fetchone()[0] == 0:
                default_words = [
                    "плохое_слово"
                ]
                for word in default_words:
                    try:
                        cursor.execute("INSERT OR IGNORE INTO banned_words (word) VALUES (?)", (word,))
                    except Exception:
                        pass

            # Вставляем стандартные теги, если таблица пуста
            cursor.execute("SELECT COUNT(*) FROM tags")
            if cursor.fetchone()[0] == 0:
                default_tags = [
                    "принципиальный", "высокомерный", "любит глумиться", "торгуется на оценку",
                    "лоялен к девушкам", "добрый", "придирчивый", "щедрый на оценки",
                    "отзывчивый", "взаимодействует онлайн", "гордый", "требовательный",
                    "уважает учащихся", "кричит", "нудный", "грубый", "интересный материал",
                    "хорошее чувство юмора", "бдительный на экзамене", "надменный",
                    "отмечает", "скромный", "неадекватный", "ставит автомат", "строгий",
                    "сложный экзамен", "адекватный", "странный", "входит в положение",
                    "конфликтный", "проверяет лекции", "злопамятный", "разрешает телефоны",
                    "общительный", "хорошие презентации", "эмоциональный", "пропускает занятия",
                    "опытный", "работал по профессии", "мотивирует", "помогает на экзамене",
                    "вежливый", "лояльный", "лоялен к парням", "хороший научный руководитель",
                    "одержим наукой"
                ]
                for tag in default_tags:
                    try:
                        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    except Exception:
                        pass

            # Вставляем стандартные вопросы, если таблица пуста
            cursor.execute("SELECT COUNT(*) FROM questions")
            if cursor.fetchone()[0] == 0:
                default_questions = [
                    (1, "Ориентирование обучающихся на будущую профессиональную деятельность",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "professional_orientation"),
                    (2, "Эффективное использование цифровых образовательных ресурсов",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "digital_resources"),
                    (3, "Понятность требований, предъявляемых к обучающимся",
                     "К сдаче зачетов и экзаменов, к курсовым, расчетно-графическим, лабораторным работам и т.п.\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "clear_requirements"),
                    (4, "Объективность и справедливость оценки учебных достижений обучающихся",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "fair_assessment"),
                    (5, "Индивидуальный подход к обучающимся",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "individual_approach"),
                    (6, "Доступность и последовательность изложения",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "clear_explanation"),
                    (7, "Организованность и пунктуальность",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "organization"),
                    (8, "Готовность оказать помощь в освоении дисциплины",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "willingness_to_help"),
                    (9, "Коммуникабельность (эффективное взаимодействие с обучающимися)",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "communication"),
                    (10, "Уважение и тактичность в отношении к обучающимся",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "respect"),
                    (11, "Умение создавать благоприятный социально-психологический климат",
                     "Оцените как проявляется это качество у преподавателя:\n\n• (5) Качество проявляется всегда\n• (4) Качество проявляется часто\n• (3) Качество проявляется скорее редко, чем часто\n• (2) Качество проявляется редко\n• (1) Качество не проявляется",
                     "positive_climate")
                ]
                for q in default_questions:
                    try:
                        cursor.execute(
                            "INSERT INTO questions (number, title, description, key) VALUES (?, ?, ?, ?)",
                            q
                        )
                    except Exception:
                        pass

            logger.info("База данных инициализирована")

    def add_user(self, id: str, username: str, full_name: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, username, full_name)
                VALUES (?, ?, ?)
            ''', (id, username, full_name))
            conn.commit()
            return cursor.lastrowid

    def get_user(self, user_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            return cursor.fetchone()

    def add_teacher(self, last_name: str, first_name: str, patronymic: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO teachers (last_name, first_name, patronymic)
                VALUES (?, ?, ?)
            ''', (last_name, first_name, patronymic))
            conn.commit()
            return cursor.lastrowid

    def update_teacher(self, teacher_id: int, **kwargs) -> bool:
        allowed_fields = ['last_name', 'first_name', 'patronymic']
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return False

        values.append(teacher_id)
        query = f"UPDATE teachers SET {', '.join(updates)} WHERE id = ?"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_teacher(self, teacher_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ratings WHERE teacher_id = ?", (teacher_id,))
            cursor.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_teachers(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teachers ORDER BY last_name, first_name, patronymic')
            return cursor.fetchall()

    def get_teacher(self, teacher_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,))
            return cursor.fetchone()

    def get_teacher_full_name(self, teacher_id: int):
        teacher = self.get_teacher(teacher_id)
        if teacher:
            parts = [teacher['last_name'], teacher['first_name']]
            if teacher['patronymic']:
                parts.append(teacher['patronymic'])
            return ' '.join(parts)
        return None

    def has_user_rated_teacher(self, user_id: int, teacher_id: int) -> bool:
        """Проверяет, оставлял ли пользователь отзыв преподавателю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM ratings WHERE user_id = ? AND teacher_id = ?",
                (user_id, teacher_id)
            )
            count = cursor.fetchone()[0]
            return count > 0

    def save_rating(self, user_id: int, teacher_id: int, score: float, tags: list, comment: str = None):
        """Сохранение оценки (сразу публикуется)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ratings (user_id, teacher_id, score, tags, comment, moderated)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (user_id, teacher_id, score, json.dumps(tags, ensure_ascii=False), comment))
            conn.commit()
            return cursor.lastrowid

    def get_teacher_ratings(self, teacher_id: int):
        """Получение всех опубликованных оценок преподавателя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ratings 
                WHERE teacher_id = ? AND moderated = 1
                ORDER BY created_at DESC
            ''', (teacher_id,))
            return cursor.fetchall()

    def get_review_by_id(self, review_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ratings WHERE id = ?", (review_id,))
            return cursor.fetchone()

    def get_teacher_stats(self, teacher_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as rating_count,
                    AVG(score) as avg_score
                FROM ratings 
                WHERE teacher_id = ? AND moderated = 1
            ''', (teacher_id,))
            return cursor.fetchone()

    def add_report(self, review_id: int, reporter_id: int, reason: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO reports (review_id, reporter_id, reason) VALUES (?, ?, ?)",
                           (review_id, reporter_id, reason))
            conn.commit()
            return cursor.lastrowid

    def get_pending_reports(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE status = 'pending' ORDER BY created_at DESC")
            return cursor.fetchall()

    def approve_report(self, report_id: int) -> bool:
        """Принять жалобу (удалить отзыв)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            report = cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            if not report:
                return False
            # Удаляем отзыв
            cursor.execute("DELETE FROM ratings WHERE id = ?", (report['review_id'],))
            # Обновляем статус жалобы
            cursor.execute("UPDATE reports SET status = 'approved', resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
                           (report_id,))
            conn.commit()
            return True

    def reject_report(self, report_id: int) -> bool:
        """Отклонить жалобу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reports SET status = 'rejected', resolved_at = CURRENT_TIMESTAMP WHERE id = ?",
                           (report_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_banned_words(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM banned_words")
            return [row['word'] for row in cursor.fetchall()]

    def add_banned_word(self, word: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO banned_words (word) VALUES (?)", (word,))
            conn.commit()

    def remove_banned_word(self, word: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM banned_words WHERE word = ?", (word,))
            conn.commit()

    def get_setting(self, key: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM moderation_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO moderation_settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_statistics(self) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ratings WHERE moderated = 1")
            total_ratings = cursor.fetchone()[0]
            cursor.execute("SELECT AVG(score) FROM ratings WHERE moderated = 1")
            avg_score = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM reports WHERE status = 'pending'")
            pending_reports = cursor.fetchone()[0]

            # Топ-10 по рейтингу
            cursor.execute("""
                SELECT t.id, t.last_name, t.first_name, t.patronymic,
                       AVG(r.score) as avg_score, COUNT(r.id) as rating_count
                FROM teachers t
                JOIN ratings r ON t.id = r.teacher_id
                WHERE r.moderated = 1
                GROUP BY t.id
                HAVING COUNT(r.id) >= 1
                ORDER BY avg_score DESC LIMIT 10
            """)
            top_by_rating = []
            for row in cursor.fetchall():
                full_name = f"{row[1]} {row[2]}"
                if row[3]: full_name += f" {row[3]}"
                top_by_rating.append({'id': row[0], 'name': full_name, 'avg_score': round(row[4], 2), 'count': row[5]})

            # Топ-10 по количеству
            cursor.execute("""
                SELECT t.id, t.last_name, t.first_name, t.patronymic,
                       AVG(r.score) as avg_score, COUNT(r.id) as rating_count
                FROM teachers t
                JOIN ratings r ON t.id = r.teacher_id
                WHERE r.moderated = 1
                GROUP BY t.id
                ORDER BY rating_count DESC LIMIT 10
            """)
            top_by_count = []
            for row in cursor.fetchall():
                full_name = f"{row[1]} {row[2]}"
                if row[3]: full_name += f" {row[3]}"
                top_by_count.append({'id': row[0], 'name': full_name, 'avg_score': round(row[4], 2), 'count': row[5]})

            return {
                'total_ratings': total_ratings,
                'avg_score': round(avg_score, 2),
                'pending_reports': pending_reports,
                'top_by_rating': top_by_rating,
                'top_by_count': top_by_count
            }

    def export_users_to_csv(self) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['id', 'username', 'full_name'])
            for user in users:
                writer.writerow([user['id'], user['username'], user['full_name']])
            return output.getvalue()

    def export_teachers_to_csv(self) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teachers")
            teachers = cursor.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['id', 'last_name', 'first_name', 'patronymic'])
            for t in teachers:
                writer.writerow([t['id'], t['last_name'], t['first_name'], t['patronymic']])
            return output.getvalue()

    def export_reviews_to_csv(self) -> str:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.id, u.full_name, t.last_name, t.first_name, t.patronymic, 
                       r.score, r.tags, r.comment, r.created_at
                FROM ratings r
                LEFT JOIN users u ON r.user_id = u.id
                LEFT JOIN teachers t ON r.teacher_id = t.id
                WHERE r.moderated = 1
            """)
            reviews = cursor.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'User', 'Teacher Last Name', 'First Name', 'Patronymic',
                             'Score', 'Tags', 'Comment', 'Date'])
            for r in reviews:
                writer.writerow([r['id'], r['full_name'], r['last_name'], r['first_name'],
                                 r['patronymic'], r['score'], r['tags'], r['comment'], r['created_at']])
            return output.getvalue()

    # ==================== УПРАВЛЕНИЕ ТЕГАМИ ====================

    def get_all_tags(self, active_only: bool = False):
        """Получение всех тегов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM tags WHERE is_active = 1 ORDER BY name")
            else:
                cursor.execute("SELECT * FROM tags ORDER BY name")
            return cursor.fetchall()

    def get_tag(self, tag_id: int):
        """Получение тега по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
            return cursor.fetchone()

    def add_tag(self, name: str) -> int:
        """Добавление нового тега"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO tags (name) VALUES (?)", (name.strip().lower(),))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return -1  # Тег уже существует

    def update_tag(self, tag_id: int, name: str = None, is_active: int = None) -> bool:
        """Обновление тега"""
        updates = []
        values = []

        if name is not None:
            updates.append("name = ?")
            values.append(name.strip().lower())
        if is_active is not None:
            updates.append("is_active = ?")
            values.append(is_active)

        if not updates:
            return False

        values.append(tag_id)
        query = f"UPDATE tags SET {', '.join(updates)} WHERE id = ?"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_tag(self, tag_id: int) -> bool:
        """Удаление тега (деактивация)"""
        return self.update_tag(tag_id, is_active=0)

    # ==================== УПРАВЛЕНИЕ ВОПРОСАМИ ====================

    def get_all_questions(self, active_only: bool = False):
        """Получение всех вопросов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute("SELECT * FROM questions WHERE is_active = 1 ORDER BY number")
            else:
                cursor.execute("SELECT * FROM questions ORDER BY number")
            return cursor.fetchall()

    def get_question(self, question_id: int):
        """Получение вопроса по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
            return cursor.fetchone()

    def add_question(self, number: int, title: str, description: str, key: str) -> int:
        """Добавление нового вопроса"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO questions (number, title, description, key) VALUES (?, ?, ?, ?)",
                    (number, title, description, key)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return -1

    def update_question(self, question_id: int, **kwargs) -> bool:
        """Обновление вопроса"""
        allowed_fields = ['number', 'title', 'description', 'key', 'is_active']
        updates = []
        values = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return False

        values.append(question_id)
        query = f"UPDATE questions SET {', '.join(updates)} WHERE id = ?"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_question(self, question_id: int) -> bool:
        """Удаление вопроса (деактивация)"""
        return self.update_question(question_id, is_active=0)

    def get_questions_count(self) -> int:
        """Получение количества активных вопросов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM questions WHERE is_active = 1")
            return cursor.fetchone()[0]


db = Database("database.db")
