"""
Migration: Proposals & Invoices Tables
Run: python migrate_proposals.py
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

print("Running proposals migration...")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposals (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        client_id       INT,
        created_by      INT NOT NULL,
        lead_name       VARCHAR(255),
        company_name    VARCHAR(255),
        email           VARCHAR(255),
        phone           VARCHAR(50),
        project_type    VARCHAR(100),
        project_description TEXT,
        budget_range    VARCHAR(100),
        timeline        VARCHAR(100),
        requirements    JSON,
        priority        VARCHAR(20) DEFAULT 'medium',
        form_data       JSON,
        proposal_text   LONGTEXT,
        status          ENUM('draft','sent','accepted','rejected') DEFAULT 'draft',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id)  REFERENCES clients(id) ON DELETE SET NULL,
        FOREIGN KEY (created_by) REFERENCES users(id)   ON DELETE CASCADE
    )
""")
print("  proposals table OK")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        proposal_id     INT,
        client_id       INT,
        created_by      INT NOT NULL,
        invoice_number  VARCHAR(50) UNIQUE NOT NULL,
        invoice_date    DATE NOT NULL,
        due_date        DATE NOT NULL,
        billed_to       JSON NOT NULL,
        billed_by       JSON NOT NULL,
        line_items      JSON NOT NULL,
        subtotal        DECIMAL(12,2) DEFAULT 0,
        tax_percent     DECIMAL(5,2)  DEFAULT 0,
        tax_amount      DECIMAL(12,2) DEFAULT 0,
        total_amount    DECIMAL(12,2) DEFAULT 0,
        payment_terms   VARCHAR(255),
        notes           TEXT,
        status          ENUM('draft','sent','paid','overdue','cancelled') DEFAULT 'draft',
        email_body      TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (proposal_id) REFERENCES proposals(id) ON DELETE SET NULL,
        FOREIGN KEY (client_id)   REFERENCES clients(id)   ON DELETE SET NULL,
        FOREIGN KEY (created_by)  REFERENCES users(id)     ON DELETE CASCADE
    )
""")
print("  invoices table OK")

conn.commit()
cursor.close()
conn.close()
print("Proposals migration complete.")
