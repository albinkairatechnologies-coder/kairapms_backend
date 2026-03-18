"""
Migration: Extend work_logs + add company_settings table
Run once: python migrate_worklogs.py
"""
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv(override=False)

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    database=os.getenv('DB_NAME', 'kairaflow')
)
cursor = conn.cursor()

def col_exists(table, col):
    cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE '{col}'")
    return cursor.fetchone() is not None

# --- work_logs extensions ---
wl_cols = {
    'team_leader_id': 'INT',
    'duration_minutes': 'INT',
    'work_date': 'DATE',
    'status': "VARCHAR(20) DEFAULT 'completed'",
    'approved_by': 'INT',
    'approved_at': 'DATETIME',
}
for col, definition in wl_cols.items():
    if not col_exists('work_logs', col):
        cursor.execute(f"ALTER TABLE work_logs ADD COLUMN {col} {definition}")
        print(f"  + work_logs.{col}")
    else:
        print(f"  ~ work_logs.{col} already exists")

# Ensure client_id, department, start_time, end_time exist (from previous migration)
prev_cols = {
    'client_id': 'INT',
    'department': 'VARCHAR(100)',
    'start_time': 'TIME',
    'end_time': 'TIME',
}
for col, definition in prev_cols.items():
    if not col_exists('work_logs', col):
        cursor.execute(f"ALTER TABLE work_logs ADD COLUMN {col} {definition}")
        print(f"  + work_logs.{col}")

# --- company_settings table ---
cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_settings (
        id INT PRIMARY KEY DEFAULT 1,
        company_name VARCHAR(200) DEFAULT 'KairaFlow',
        company_address TEXT,
        company_phone VARCHAR(50),
        company_email VARCHAR(200),
        company_website VARCHAR(200),
        company_logo_path VARCHAR(500),
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
""")
cursor.execute("SELECT COUNT(*) FROM company_settings")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
        INSERT INTO company_settings (id, company_name, company_address, company_phone, company_email, company_website)
        VALUES (1, %s, %s, %s, %s, %s)
    """, (
        os.getenv('COMPANY_NAME', 'KairaFlow'),
        os.getenv('COMPANY_ADDRESS', ''),
        os.getenv('COMPANY_PHONE', ''),
        os.getenv('COMPANY_EMAIL', ''),
        os.getenv('COMPANY_WEBSITE', ''),
    ))
    print("  + company_settings seeded")

conn.commit()
cursor.close()
conn.close()
print("Migration complete.")
