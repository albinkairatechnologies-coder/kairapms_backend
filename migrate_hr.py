"""
Migration: HR & Productivity Monitoring Tables
Run: python migrate_hr.py
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'agencyflow')

conn = mysql.connector.connect(
    host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
)
cursor = conn.cursor()

def column_exists(table, column):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (DB_NAME, table, column))
    return cursor.fetchone()[0] > 0

print("Running HR migration...")

# ── 1. Attendance ─────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        date             DATE NOT NULL,
        check_in_time    DATETIME,
        check_out_time   DATETIME,
        total_hours      DECIMAL(5,2) DEFAULT 0,
        break_minutes    INT DEFAULT 0,
        net_hours        DECIMAL(5,2) DEFAULT 0,
        status           ENUM('present','late','half_day','absent','on_leave') DEFAULT 'present',
        late_by_minutes  INT DEFAULT 0,
        notes            TEXT,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_date (user_id, date),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  attendance table OK")

# ── 2. Breaks ─────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS breaks (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        attendance_id    INT NOT NULL,
        break_type       ENUM('lunch','short') NOT NULL,
        break_start      DATETIME NOT NULL,
        break_end        DATETIME,
        duration_minutes INT,
        status           ENUM('active','completed') DEFAULT 'active',
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (attendance_id) REFERENCES attendance(id) ON DELETE CASCADE
    )
""")
print("  breaks table OK")

# ── 3. Leave Requests ─────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        leave_type       ENUM('sick','casual','emergency','annual') NOT NULL,
        start_date       DATE NOT NULL,
        end_date         DATE NOT NULL,
        total_days       INT DEFAULT 1,
        reason           TEXT NOT NULL,
        status           ENUM('pending','approved','rejected') DEFAULT 'pending',
        approved_by      INT,
        approved_at      DATETIME,
        rejection_note   TEXT,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
    )
""")
print("  leave_requests table OK")

# ── 4. Permission Requests ────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS permission_requests (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        date             DATE NOT NULL,
        from_time        TIME NOT NULL,
        to_time          TIME NOT NULL,
        duration_minutes INT,
        reason           TEXT NOT NULL,
        status           ENUM('pending','approved','rejected') DEFAULT 'pending',
        approved_by      INT,
        approved_at      DATETIME,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
    )
""")
print("  permission_requests table OK")

# ── 5. Feedback ───────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        category         ENUM('work_environment','team_issue','suggestion','general') NOT NULL,
        message          TEXT NOT NULL,
        rating           TINYINT CHECK (rating BETWEEN 1 AND 5),
        visibility       ENUM('anonymous','named') DEFAULT 'named',
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  feedback table OK")

# ── 6. Review Meetings ────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_meetings (
        id                  INT AUTO_INCREMENT PRIMARY KEY,
        employee_id         INT NOT NULL,
        reviewer_id         INT NOT NULL,
        meeting_date        DATE NOT NULL,
        meeting_type        ENUM('monthly','quarterly','annual','probation') DEFAULT 'monthly',
        rating              TINYINT CHECK (rating BETWEEN 1 AND 5),
        notes               TEXT,
        improvement_points  TEXT,
        goals_set           TEXT,
        status              ENUM('scheduled','completed','cancelled') DEFAULT 'scheduled',
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  review_meetings table OK")

# ── 7. Company settings HR columns ───────────────────────────
hr_columns = [
    ("work_start_time",     "TIME DEFAULT '09:00:00'"),
    ("work_end_time",       "TIME DEFAULT '18:00:00'"),
    ("late_threshold_min",  "INT DEFAULT 15"),
    ("lunch_break_max_min", "INT DEFAULT 60"),
    ("short_break_max_min", "INT DEFAULT 15"),
    ("idle_alert_minutes",  "INT DEFAULT 10"),
]
for col, definition in hr_columns:
    if not column_exists('company_settings', col):
        cursor.execute(f"ALTER TABLE company_settings ADD COLUMN {col} {definition}")
        print(f"  Added company_settings.{col}")
    else:
        print(f"  company_settings.{col} already exists")

conn.commit()
cursor.close()
conn.close()
print("\nHR migration complete!")
