"""
Student Attendance Management System
Software Engineering Course Project - Working Prototype
Tech Stack: Python Flask + SQLite + Bootstrap 5
"""

import os
import sqlite3
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "se-course-project-change-in-production-2026"
DATABASE = os.path.join(os.path.dirname(__file__), "attendance.db")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'lecturer', 'student')),
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            lecturer_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lecturer_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            session_date TEXT NOT NULL,
            topic TEXT,
            created_by INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id, session_date),
            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
            marked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, student_id),
            FOREIGN KEY (session_id) REFERENCES attendance_sessions(id),
            FOREIGN KEY (student_id) REFERENCES users(id)
        );
    """)
    db.commit()

    # Seed data only if empty
    cur = db.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        seed_data(db)
    db.close()


def seed_data(db):
    """Create demo users, courses, enrollments and sample attendance."""
    users = [
        ("admin", "admin@school.edu", generate_password_hash("admin123"), "System Administrator", "admin"),
        ("lecturer1", "john.doe@school.edu", generate_password_hash("lect123"), "Dr. John Doe", "lecturer"),
        ("lecturer2", "jane.smith@school.edu", generate_password_hash("lect123"), "Prof. Jane Smith", "lecturer"),
        ("student1", "alice@student.edu", generate_password_hash("stud123"), "Alice Johnson", "student"),
        ("student2", "bob@student.edu", generate_password_hash("stud123"), "Bob Smith", "student"),
        ("student3", "carol@student.edu", generate_password_hash("stud123"), "Carol Williams", "student"),
        ("student4", "david@student.edu", generate_password_hash("stud123"), "David Brown", "student"),
        ("student5", "eva@student.edu", generate_password_hash("stud123"), "Eva Davis", "student"),
    ]
    db.executemany(
        "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
        users
    )

    courses = [
        ("CS101", "Introduction to Programming", "Basics of programming with Python", 2),
        ("MATH201", "Calculus I", "Differential and integral calculus", 3),
        ("ENG105", "Academic Writing", "Writing skills for university", 2),
    ]
    db.executemany(
        "INSERT INTO courses (code, title, description, lecturer_id) VALUES (?, ?, ?, ?)",
        courses
    )

    # Enroll students 4-8 into courses
    enrollments = [
        (4, 1), (5, 1), (6, 1), (7, 1), (8, 1),  # CS101
        (4, 2), (5, 2), (6, 2),                   # MATH201
        (4, 3), (7, 3), (8, 3),                   # ENG105
    ]
    db.executemany(
        "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
        enrollments
    )

    # Sample session + records for CS101
    db.execute(
        "INSERT INTO attendance_sessions (course_id, session_date, topic, created_by) VALUES (1, '2026-08-05', 'Variables and Data Types', 2)"
    )
    session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    records = [
        (session_id, 4, "Present"),
        (session_id, 5, "Present"),
        (session_id, 6, "Late"),
        (session_id, 7, "Absent"),
        (session_id, 8, "Present"),
    ]
    db.executemany(
        "INSERT INTO attendance_records (session_id, student_id, status) VALUES (?, ?, ?)",
        records
    )
    db.commit()
    print("Database seeded with demo data.")


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                if isinstance(role, (list, tuple)):
                    if session.get("role") not in role:
                        flash("You do not have permission to access that page.", "danger")
                        return redirect(url_for("dashboard"))
                else:
                    flash("You do not have permission to access that page.", "danger")
                    return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()


# ---------------------------------------------------------------------------
# Routes - Auth
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE (username = ? OR email = ?) AND is_active = 1",
            (username, username)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username/email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required()
def dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif role == "lecturer":
        return redirect(url_for("lecturer_dashboard"))
    else:
        return redirect(url_for("student_dashboard"))


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@app.route("/admin")
@login_required("admin")
def admin_dashboard():
    db = get_db()
    stats = {
        "users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "courses": db.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "sessions": db.execute("SELECT COUNT(*) FROM attendance_sessions").fetchone()[0],
        "records": db.execute("SELECT COUNT(*) FROM attendance_records").fetchone()[0],
    }
    recent_users = db.execute(
        "SELECT id, full_name, role, email, is_active FROM users ORDER BY id DESC LIMIT 5"
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, recent_users=recent_users)


@app.route("/admin/users")
@login_required("admin")
def admin_users():
    db = get_db()
    users = db.execute(
        "SELECT id, username, email, full_name, role, is_active, created_at FROM users ORDER BY role, full_name"
    ).fetchall()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "")
        password = request.form.get("password", "")

        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("Valid email is required.")
        if not full_name:
            errors.append("Full name is required.")
        if role not in ("admin", "lecturer", "student"):
            errors.append("Invalid role.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/add_user.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
                (username, email, generate_password_hash(password), full_name, role)
            )
            db.commit()
            flash(f"User '{full_name}' created successfully.", "success")
            return redirect(url_for("admin_users"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "danger")

    return render_template("admin/add_user.html")


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required("admin")
def admin_toggle_user(user_id):
    if user_id == session["user_id"]:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin_users"))
    db = get_db()
    user = db.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
        db.commit()
        flash("User status updated.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/courses")
@login_required("admin")
def admin_courses():
    db = get_db()
    courses = db.execute("""
        SELECT c.*, u.full_name AS lecturer_name,
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id) AS student_count
        FROM courses c
        LEFT JOIN users u ON c.lecturer_id = u.id
        ORDER BY c.code
    """).fetchall()
    return render_template("admin/courses.html", courses=courses)


@app.route("/admin/courses/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_course():
    db = get_db()
    lecturers = db.execute(
        "SELECT id, full_name FROM users WHERE role = 'lecturer' AND is_active = 1 ORDER BY full_name"
    ).fetchall()

    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        lecturer_id = request.form.get("lecturer_id") or None

        if not code or not title:
            flash("Course code and title are required.", "danger")
            return render_template("admin/add_course.html", lecturers=lecturers)

        try:
            db.execute(
                "INSERT INTO courses (code, title, description, lecturer_id) VALUES (?, ?, ?, ?)",
                (code, title, description, lecturer_id)
            )
            db.commit()
            flash(f"Course {code} created successfully.", "success")
            return redirect(url_for("admin_courses"))
        except sqlite3.IntegrityError:
            flash("Course code already exists.", "danger")

    return render_template("admin/add_course.html", lecturers=lecturers)


@app.route("/admin/courses/<int:course_id>/enroll", methods=["GET", "POST"])
@login_required("admin")
def admin_enroll(course_id):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        abort(404)

    if request.method == "POST":
        student_id = request.form.get("student_id")
        if student_id:
            try:
                db.execute(
                    "INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)",
                    (student_id, course_id)
                )
                db.commit()
                flash("Student enrolled successfully.", "success")
            except sqlite3.IntegrityError:
                flash("Student is already enrolled in this course.", "warning")
        return redirect(url_for("admin_enroll", course_id=course_id))

    enrolled = db.execute("""
        SELECT u.id, u.full_name, u.email, e.enrolled_at
        FROM enrollments e JOIN users u ON e.student_id = u.id
        WHERE e.course_id = ? ORDER BY u.full_name
    """, (course_id,)).fetchall()

    available = db.execute("""
        SELECT id, full_name, email FROM users
        WHERE role = 'student' AND is_active = 1
          AND id NOT IN (SELECT student_id FROM enrollments WHERE course_id = ?)
        ORDER BY full_name
    """, (course_id,)).fetchall()

    return render_template("admin/enroll.html", course=course, enrolled=enrolled, available=available)


# ---------------------------------------------------------------------------
# Lecturer routes
# ---------------------------------------------------------------------------
@app.route("/lecturer")
@login_required("lecturer")
def lecturer_dashboard():
    db = get_db()
    courses = db.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM enrollments e WHERE e.course_id = c.id) AS student_count,
               (SELECT COUNT(*) FROM attendance_sessions s WHERE s.course_id = c.id) AS session_count
        FROM courses c
        WHERE c.lecturer_id = ?
        ORDER BY c.code
    """, (session["user_id"],)).fetchall()
    return render_template("lecturer/dashboard.html", courses=courses)


@app.route("/lecturer/course/<int:course_id>")
@login_required("lecturer")
def lecturer_course(course_id):
    db = get_db()
    course = db.execute(
        "SELECT * FROM courses WHERE id = ? AND lecturer_id = ?",
        (course_id, session["user_id"])
    ).fetchone()
    if not course:
        flash("Course not found or access denied.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    sessions = db.execute("""
        SELECT s.*, 
               (SELECT COUNT(*) FROM attendance_records r WHERE r.session_id = s.id) AS record_count
        FROM attendance_sessions s
        WHERE s.course_id = ?
        ORDER BY s.session_date DESC
    """, (course_id,)).fetchall()

    return render_template("lecturer/course.html", course=course, sessions=sessions)


@app.route("/lecturer/course/<int:course_id>/session/new", methods=["GET", "POST"])
@login_required("lecturer")
def lecturer_new_session(course_id):
    db = get_db()
    course = db.execute(
        "SELECT * FROM courses WHERE id = ? AND lecturer_id = ?",
        (course_id, session["user_id"])
    ).fetchone()
    if not course:
        flash("Course not found or access denied.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    if request.method == "POST":
        session_date = request.form.get("session_date", "").strip()
        topic = request.form.get("topic", "").strip()

        if not session_date:
            flash("Session date is required.", "danger")
            return render_template("lecturer/new_session.html", course=course, today=date.today().isoformat())

        try:
            db.execute(
                "INSERT INTO attendance_sessions (course_id, session_date, topic, created_by) VALUES (?, ?, ?, ?)",
                (course_id, session_date, topic, session["user_id"])
            )
            db.commit()
            session_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            flash("Session created. Now mark attendance.", "success")
            return redirect(url_for("lecturer_mark", session_id=session_id))
        except sqlite3.IntegrityError:
            flash("A session for this date already exists.", "warning")
            existing = db.execute(
                "SELECT id FROM attendance_sessions WHERE course_id = ? AND session_date = ?",
                (course_id, session_date)
            ).fetchone()
            if existing:
                return redirect(url_for("lecturer_mark", session_id=existing["id"]))

    return render_template("lecturer/new_session.html", course=course, today=date.today().isoformat())


@app.route("/lecturer/session/<int:session_id>/mark", methods=["GET", "POST"])
@login_required("lecturer")
def lecturer_mark(session_id):
    db = get_db()
    sess = db.execute("""
        SELECT s.*, c.code, c.title, c.lecturer_id
        FROM attendance_sessions s JOIN courses c ON s.course_id = c.id
        WHERE s.id = ?
    """, (session_id,)).fetchone()

    if not sess or sess["lecturer_id"] != session["user_id"]:
        flash("Session not found or access denied.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    students = db.execute("""
        SELECT u.id, u.full_name, u.email,
               (SELECT status FROM attendance_records r 
                WHERE r.session_id = ? AND r.student_id = u.id) AS current_status
        FROM enrollments e JOIN users u ON e.student_id = u.id
        WHERE e.course_id = ?
        ORDER BY u.full_name
    """, (session_id, sess["course_id"])).fetchall()

    if request.method == "POST":
        for student in students:
            status = request.form.get(f"status_{student['id']}")
            if status in ("Present", "Absent", "Late"):
                existing = db.execute(
                    "SELECT id FROM attendance_records WHERE session_id = ? AND student_id = ?",
                    (session_id, student["id"])
                ).fetchone()
                if existing:
                    db.execute(
                        "UPDATE attendance_records SET status = ?, marked_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (status, existing["id"])
                    )
                else:
                    db.execute(
                        "INSERT INTO attendance_records (session_id, student_id, status) VALUES (?, ?, ?)",
                        (session_id, student["id"], status)
                    )
        db.commit()
        flash("Attendance saved successfully.", "success")
        return redirect(url_for("lecturer_course", course_id=sess["course_id"]))

    return render_template("lecturer/mark.html", sess=sess, students=students)


@app.route("/lecturer/session/<int:session_id>/report")
@login_required("lecturer")
def lecturer_session_report(session_id):
    db = get_db()
    sess = db.execute("""
        SELECT s.*, c.code, c.title, c.lecturer_id
        FROM attendance_sessions s JOIN courses c ON s.course_id = c.id
        WHERE s.id = ?
    """, (session_id,)).fetchone()

    if not sess or sess["lecturer_id"] != session["user_id"]:
        flash("Access denied.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    records = db.execute("""
        SELECT u.full_name, u.email, r.status, r.marked_at
        FROM attendance_records r JOIN users u ON r.student_id = u.id
        WHERE r.session_id = ?
        ORDER BY u.full_name
    """, (session_id,)).fetchall()

    summary = {"Present": 0, "Absent": 0, "Late": 0}
    for r in records:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    return render_template("lecturer/report.html", sess=sess, records=records, summary=summary)


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------
@app.route("/student")
@login_required("student")
def student_dashboard():
    db = get_db()
    courses = db.execute("""
        SELECT c.id, c.code, c.title,
               (SELECT COUNT(*) FROM attendance_sessions s WHERE s.course_id = c.id) AS total_sessions,
               (SELECT COUNT(*) FROM attendance_records r
                JOIN attendance_sessions s ON r.session_id = s.id
                WHERE s.course_id = c.id AND r.student_id = ? AND r.status = 'Present') AS present_count,
               (SELECT COUNT(*) FROM attendance_records r
                JOIN attendance_sessions s ON r.session_id = s.id
                WHERE s.course_id = c.id AND r.student_id = ? AND r.status = 'Late') AS late_count
        FROM courses c
        JOIN enrollments e ON e.course_id = c.id
        WHERE e.student_id = ?
        ORDER BY c.code
    """, (session["user_id"], session["user_id"], session["user_id"])).fetchall()

    # Compute percentages
    course_list = []
    for c in courses:
        total = c["total_sessions"] or 0
        present = (c["present_count"] or 0) + (c["late_count"] or 0)  # Late counts as attended
        pct = round((present / total * 100), 1) if total > 0 else 0
        course_list.append({
            "id": c["id"], "code": c["code"], "title": c["title"],
            "total": total, "present": c["present_count"] or 0,
            "late": c["late_count"] or 0, "percentage": pct
        })

    return render_template("student/dashboard.html", courses=course_list)


@app.route("/student/course/<int:course_id>")
@login_required("student")
def student_course_detail(course_id):
    db = get_db()
    # Verify enrollment
    enrolled = db.execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ?",
        (session["user_id"], course_id)
    ).fetchone()
    if not enrolled:
        flash("You are not enrolled in this course.", "danger")
        return redirect(url_for("student_dashboard"))

    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    records = db.execute("""
        SELECT s.session_date, s.topic, r.status, r.marked_at
        FROM attendance_sessions s
        LEFT JOIN attendance_records r ON r.session_id = s.id AND r.student_id = ?
        WHERE s.course_id = ?
        ORDER BY s.session_date DESC
    """, (session["user_id"], course_id)).fetchall()

    return render_template("student/course_detail.html", course=course, records=records)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("Student Attendance Management System")
    print("Demo accounts:")
    print("  Admin    : admin / admin123")
    print("  Lecturer : lecturer1 / lect123")
    print("  Student  : student1 / stud123")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
