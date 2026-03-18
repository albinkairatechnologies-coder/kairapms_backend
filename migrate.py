"""
Migration: Upgrade to Hierarchical Team Task Management System
Run: python migrate.py
"""
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'kairaflow')
)
cursor = conn.cursor()

def column_exists(table, column):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (os.getenv('DB_NAME', 'kairaflow'), table, column))
    return cursor.fetchone()[0] > 0

print("Running migration...")

# 1. Teams table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 2. Departments table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        team_id INT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
    )
""")

# 3. Task activity log table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_activity (
        id INT AUTO_INCREMENT PRIMARY KEY,
        task_id INT NOT NULL,
        user_id INT NOT NULL,
        action VARCHAR(255) NOT NULL,
        old_value TEXT,
        new_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")

# 4. Alter users - add columns if missing
if not column_exists('users', 'team_id'):
    cursor.execute("ALTER TABLE users ADD COLUMN team_id INT DEFAULT NULL")
    print("  Added users.team_id")
if not column_exists('users', 'department_id'):
    cursor.execute("ALTER TABLE users ADD COLUMN department_id INT DEFAULT NULL")
    print("  Added users.department_id")
if not column_exists('users', 'manager_id'):
    cursor.execute("ALTER TABLE users ADD COLUMN manager_id INT DEFAULT NULL")
    print("  Added users.manager_id")

# 5. Update users role ENUM
try:
    cursor.execute("""
        ALTER TABLE users MODIFY COLUMN role 
        ENUM('admin','marketing_head','developer','smm','crm','client','team_lead','employee') NOT NULL
    """)
    print("  Updated users.role ENUM")
except Exception as e:
    print(f"  Role enum: {e}")

# 6. Alter tasks - add columns if missing
if not column_exists('tasks', 'assigned_by'):
    cursor.execute("ALTER TABLE tasks ADD COLUMN assigned_by INT DEFAULT NULL")
    print("  Added tasks.assigned_by")
if not column_exists('tasks', 'team_id'):
    cursor.execute("ALTER TABLE tasks ADD COLUMN team_id INT DEFAULT NULL")
    print("  Added tasks.team_id")
if not column_exists('tasks', 'department_id'):
    cursor.execute("ALTER TABLE tasks ADD COLUMN department_id INT DEFAULT NULL")
    print("  Added tasks.department_id")

# 7. Update tasks status ENUM to include 'review'
try:
    cursor.execute("""
        ALTER TABLE tasks MODIFY COLUMN status 
        ENUM('pending','in_progress','review','completed') DEFAULT 'pending'
    """)
    print("  Updated tasks.status ENUM")
except Exception as e:
    print(f"  Status enum: {e}")

# 8. Update tasks department ENUM
try:
    cursor.execute("""
        ALTER TABLE tasks MODIFY COLUMN department 
        ENUM('marketing','smm','crm','development','video_editing','web_development','general') NOT NULL DEFAULT 'general'
    """)
    print("  Updated tasks.department ENUM")
except Exception as e:
    print(f"  Department enum: {e}")

# 9. Make tasks.client_id nullable
try:
    cursor.execute("ALTER TABLE tasks MODIFY COLUMN client_id INT DEFAULT NULL")
    print("  Made tasks.client_id nullable")
except Exception as e:
    print(f"  client_id nullable: {e}")

# 10. Seed default teams and departments if empty
cursor.execute("SELECT COUNT(*) FROM teams")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO teams (name, description) VALUES ('Marketing Team', 'Handles all marketing campaigns')")
    marketing_team_id = cursor.lastrowid
    cursor.execute("INSERT INTO teams (name, description) VALUES ('CRM Team', 'Client relationship and delivery')")
    crm_team_id = cursor.lastrowid
    cursor.execute("INSERT INTO departments (name, team_id, description) VALUES ('Video Editing', %s, 'Video production and editing')", (crm_team_id,))
    cursor.execute("INSERT INTO departments (name, team_id, description) VALUES ('Social Media Marketing', %s, 'Social media management')", (crm_team_id,))
    cursor.execute("INSERT INTO departments (name, team_id, description) VALUES ('Web Development', %s, 'Website design and development')", (crm_team_id,))
    print("  Seeded default teams and departments.")
else:
    print("  Teams already seeded, skipping.")

conn.commit()
cursor.close()
conn.close()
print("Migration complete!")
