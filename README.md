# Student Attendance Management System

**Software Engineering Course Project – Working Prototype**

## Tech Stack
- Backend: Python 3 + Flask
- Database: SQLite
- Frontend: Bootstrap 5 + Jinja2 templates
- Auth: Session-based with Werkzeug password hashing

## Features Implemented
- Role-based access (Administrator, Lecturer, Student)
- User management (Admin)
- Course & enrollment management (Admin)
- Create attendance sessions & mark Present / Absent / Late (Lecturer)
- View personal attendance summary & percentage (Student)
- Session reports
- Input validation, flash messages, basic security

## Quick Start

```bash
cd student_attendance
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Demo Accounts

| Role      | Username   | Password  |
|-----------|------------|-----------|
| Admin     | admin      | admin123  |
| Lecturer  | lecturer1  | lect123   |
| Student   | student1   | stud123   |

Additional students: `student2` … `student5` (password `stud123`)  
Additional lecturer: `lecturer2` / `lect123`

## Project Structure
```
student_attendance/
├── app.py              # Main application (routes, models, logic)
├── attendance.db       # SQLite database (created on first run)
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── admin/
│   ├── lecturer/
│   └── student/
└── static/
```

## Notes for Team / Submission
- All source code is under version control (commit this folder to GitHub).
- Database file `attendance.db` is generated automatically with seed data.
- Passwords are hashed (Werkzeug).
- The prototype demonstrates core functional requirements from the SRS.
