View Database

import sqlite3
from tabulate import tabulate

def view_database():
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    try:
        # View Students
        print("\n=== Students ===")
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        print(tabulate(students, headers=['ID', 'Name', 'Created At']))

        # View Lectures
        print("\n=== Lectures ===")
        cursor.execute("SELECT * FROM lectures")
        lectures = cursor.fetchall()
        print(tabulate(lectures, headers=['ID', 'Name', 'Date', 'Created At']))

        # View Attendance
        print("\n=== Attendance Records ===")
        cursor.execute("""
            SELECT
                s.name as Student,
                l.name as Lecture,
                l.date as Date,
                a.status as Status,
                a.marked_at as 'Marked At'
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            JOIN lectures l ON a.lecture_id = l.id
        """)
        attendance = cursor.fetchall()
        print(tabulate(attendance, headers=['Student', 'Lecture', 'Date', 'Status', 'Marked At']))

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if _name_ == "_main_":
    view_database()
