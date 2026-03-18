"""
Migration: Smart Notifications Table
Run: python migrate_notifications.py
"""
import mysql.connector, os
from dotenv import load_dotenv

load_dotenv(override=False)

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    database=os.getenv('DB_NAME', 'agencyflow'),
)
cursor = conn.cursor()

print("Running notifications migration...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NOT NULL,
        type        VARCHAR(50) NOT NULL,
        title       VARCHAR(255) NOT NULL,
        message     TEXT NOT NULL,
        link        VARCHAR(255),
        is_read     TINYINT(1) DEFAULT 0,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")
print("  notifications table OK")

conn.commit()
cursor.close()
conn.close()
print("Notifications migration complete!")
