"""
Migration: Send Proposal — add template_id, sent_at, viewed_at, note to proposals
Run: python migrate_send_proposal.py
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

def col_exists(table, col):
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
    """, (os.getenv('DB_NAME','agencyflow'), table, col))
    return cursor.fetchone()[0] > 0

print("Running send-proposal migration...")

cols = [
    ("template_id",   "VARCHAR(60)"),
    ("template_name", "VARCHAR(120)"),
    ("note",          "TEXT"),
    ("sent_at",       "DATETIME"),
    ("viewed_at",     "DATETIME"),
    ("sent_by",       "INT"),
]
for col, defn in cols:
    if not col_exists('proposals', col):
        cursor.execute(f"ALTER TABLE proposals ADD COLUMN {col} {defn}")
        print(f"  Added proposals.{col}")
    else:
        print(f"  proposals.{col} already exists")

# Extend status enum to include 'viewed'
cursor.execute("""
    ALTER TABLE proposals
    MODIFY COLUMN status ENUM('draft','sent','viewed','accepted','rejected') DEFAULT 'draft'
""")
print("  proposals.status enum updated")

conn.commit()
cursor.close(); conn.close()
print("Send-proposal migration complete!")
