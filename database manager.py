Database manager

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

class DatabaseManager:
    def _init_(self, db_path: str = "attendance.db"):
        self.db_path = db_path
        self.init_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create tables
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS lectures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date DATE NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, date)
                );

                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    lecture_id INTEGER,
                    status TEXT DEFAULT 'Present',
                    marked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(id),
                    FOREIGN KEY (lecture_id) REFERENCES lectures(id),
                    UNIQUE(student_id, lecture_id)
                );
            """)
            conn.commit()

    def add_student(self, name: str) -> Optional[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO students (name) VALUES (?)",
                    (name,)
                )
                conn.commit()
                cursor.execute("SELECT id FROM students WHERE name = ?", (name,))
                result = cursor.fetchone()
                return result['id'] if result else None
            except sqlite3.Error as e:
                print(f"Error adding student: {e}")
                return None

    def add_lecture(self, name: str, date: str) -> Optional[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO lectures (name, date) VALUES (?, ?)",
                    (name, date)
                )
                conn.commit()
                cursor.execute(
                    "SELECT id FROM lectures WHERE name = ? AND date = ?",
                    (name, date)
                )
                result = cursor.fetchone()
                return result['id'] if result else None
            except sqlite3.Error as e:
                print(f"Error adding lecture: {e}")
                return None

    def mark_attendance(self, student_name: str, lecture_name: str, date: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Get or create student
                cursor.execute("SELECT id FROM students WHERE name = ?", (student_name,))
                student = cursor.fetchone()
                if not student:
                    student_id = self.add_student(student_name)
                else:
                    student_id = student['id']

                # Get or create lecture
                cursor.execute(
                    "SELECT id FROM lectures WHERE name = ? AND date = ?",
                    (lecture_name, date)
                )
                lecture = cursor.fetchone()
                if not lecture:
                    lecture_id = self.add_lecture(lecture_name, date)
                else:
                    lecture_id = lecture['id']

                if student_id and lecture_id:
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance (student_id, lecture_id)
                        VALUES (?, ?)
                    """, (student_id, lecture_id))
                    conn.commit()
                    return True
                return False
            except sqlite3.Error as e:
                print(f"Error marking attendance: {e}")
                return False

    def get_attendance_report(self, lecture_name: str, date: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    s.name as student_name,
                    l.name as lecture_name,
                    l.date as lecture_date,
                    a.status,
                    a.marked_at
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                JOIN lectures l ON a.lecture_id = l.id
                WHERE l.name = ? AND l.date = ?
            """, (lecture_name, date))
            return [dict(row) for row in cursor.fetchall()]

    def get_all_students(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_lectures(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lectures")
            return [dict(row) for row in cursor.fetchall()]
