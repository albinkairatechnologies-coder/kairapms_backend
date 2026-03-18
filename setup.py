"""
Setup: Create default admin user
Run: python setup.py
"""
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv(override=False)

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    database=os.getenv('DB_NAME', 'agencyflow'),
)
cursor = conn.cursor()

# Create users table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        name          VARCHAR(255) NOT NULL,
        email         VARCHAR(255) UNIQUE NOT NULL,
        password      VARCHAR(255) NOT NULL,
        role          ENUM('admin','marketing_head','developer','smm','crm','client','team_lead','employee') NOT NULL DEFAULT 'employee',
        phone         VARCHAR(50),
        team_id       INT DEFAULT NULL,
        department_id INT DEFAULT NULL,
        manager_id    INT DEFAULT NULL,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  users table OK")

# Create clients table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        name         VARCHAR(255) NOT NULL,
        email        VARCHAR(255) UNIQUE NOT NULL,
        password     VARCHAR(255) NOT NULL,
        company_name VARCHAR(255),
        phone        VARCHAR(50),
        address      TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  clients table OK")

# Create tasks table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        title         VARCHAR(255) NOT NULL,
        description   TEXT,
        assigned_to   INT,
        assigned_by   INT DEFAULT NULL,
        client_id     INT DEFAULT NULL,
        team_id       INT DEFAULT NULL,
        department_id INT DEFAULT NULL,
        department    ENUM('marketing','smm','crm','development','video_editing','web_development','general') NOT NULL DEFAULT 'general',
        priority      ENUM('low','medium','high','urgent') DEFAULT 'medium',
        status        ENUM('pending','in_progress','review','completed') DEFAULT 'pending',
        due_date      DATE,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
    )
""")
print("  tasks table OK")

# Create work_logs table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_logs (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        user_id          INT NOT NULL,
        task_id          INT,
        client_id        INT,
        department       VARCHAR(100),
        description      TEXT NOT NULL,
        start_time       TIME,
        end_time         TIME,
        duration_minutes INT,
        work_date        DATE,
        status           VARCHAR(20) DEFAULT 'completed',
        team_leader_id   INT,
        approved_by      INT,
        approved_at      DATETIME,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  work_logs table OK")

conn.commit()

# Seed admin user
try:
    hashed = generate_password_hash('admin123', method='pbkdf2:sha256')
    cursor.execute(
        "INSERT INTO users (name, email, password, role, phone) VALUES (%s, %s, %s, %s, %s)",
        ('Admin User', 'admin@agency.com', hashed, 'admin', '1234567890')
    )
    conn.commit()
    print("  Admin user created: admin@agency.com / admin123")
except Exception as e:
    print(f"  Admin user already exists, skipping: {e}")

cursor.close()
conn.close()
print("Setup complete!")
