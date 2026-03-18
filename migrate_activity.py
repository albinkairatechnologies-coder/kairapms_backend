"""
Migration: Activity Tracking Tables
Run: python migrate_activity.py
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'agencyflow')

conn   = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
cursor = conn.cursor()

print("Running activity migration...")

# ── 1. activity_logs ──────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id               BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        timestamp        DATETIME NOT NULL,
        activity_type    ENUM('mouse','keyboard','idle','active') NOT NULL,
        duration_seconds INT DEFAULT 0,
        INDEX idx_user_ts (user_id, timestamp),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  activity_logs table OK")

# ── 2. employee_status (live state, upserted every 30s) ───────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_status (
        user_id                INT PRIMARY KEY,
        status                 ENUM('online','active','idle','away','offline') DEFAULT 'offline',
        last_active            DATETIME,
        last_heartbeat         DATETIME,
        today_active_seconds   INT DEFAULT 0,
        today_idle_seconds     INT DEFAULT 0,
        productivity_score     DECIMAL(5,2) DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  employee_status table OK")

conn.commit()
cursor.close()
conn.close()
print("\nActivity migration complete!")
