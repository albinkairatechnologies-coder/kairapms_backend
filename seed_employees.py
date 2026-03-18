"""
Seed: Add Team Leads + 2 Employees per Team/Department
Run: python seed_employees.py
"""
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'kairaflow')
)
cursor = conn.cursor()

def add_user(name, email, role, team_id=None, department_id=None, manager_id=None, password='password123'):
    hashed = generate_password_hash(password)
    cursor.execute("""
        INSERT INTO users (name, email, password, role, team_id, department_id, manager_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (name, email, hashed, role, team_id, department_id, manager_id))
    conn.commit()
    return cursor.lastrowid

print("Seeding employees...")

# ── Update existing users to assign to teams ──────────────
# John Marketing → Marketing Team Lead (team_id=1)
cursor.execute("UPDATE users SET role='team_lead', team_id=1 WHERE id=2")
# Sarah Sales → CRM Team Lead (team_id=2)
cursor.execute("UPDATE users SET role='team_lead', team_id=2 WHERE id=5")
# Jane Developer → Web Development dept (dept_id=3, team_id=2)
cursor.execute("UPDATE users SET team_id=2, department_id=3, manager_id=5 WHERE id=3")
# Mike Social → Social Media dept (dept_id=2, team_id=2)
cursor.execute("UPDATE users SET team_id=2, department_id=2, manager_id=5 WHERE id=4")
conn.commit()
print("  Updated existing users to teams.")

# ── Marketing Team (team_id=1) ─────────────────────────────
# Team Lead already: John Marketing (id=2)
# 2 Marketing Employees
emp1 = add_user('Alice Carter',   'alice@agency.com',   'employee', team_id=1, manager_id=2)
emp2 = add_user('Bob Williams',   'bob@agency.com',     'employee', team_id=1, manager_id=2)
print(f"  Marketing Team: Alice (id={emp1}), Bob (id={emp2})")

# ── CRM Team (team_id=2) ───────────────────────────────────
# Team Lead already: Sarah Sales (id=5)
# 2 CRM-level employees (no specific dept)
emp3 = add_user('Carol Davis',    'carol@agency.com',   'employee', team_id=2, manager_id=5)
emp4 = add_user('David Lee',      'david@agency.com',   'employee', team_id=2, manager_id=5)
print(f"  CRM Team: Carol (id={emp3}), David (id={emp4})")

# ── Video Editing Dept (dept_id=1, team_id=2) ─────────────
# Add a Video Editing Team Lead
ve_lead = add_user('Emma Wilson',  'emma@agency.com',   'team_lead', team_id=2, department_id=1, manager_id=5)
# 2 Video Editors
emp5 = add_user('Frank Moore',    'frank@agency.com',   'employee', team_id=2, department_id=1, manager_id=ve_lead)
emp6 = add_user('Grace Taylor',   'grace@agency.com',   'employee', team_id=2, department_id=1, manager_id=ve_lead)
print(f"  Video Editing: Lead=Emma (id={ve_lead}), Frank (id={emp5}), Grace (id={emp6})")

# ── Social Media Marketing Dept (dept_id=2, team_id=2) ────
# Mike Social already assigned to this dept (id=4), promote to team_lead
cursor.execute("UPDATE users SET role='team_lead' WHERE id=4")
conn.commit()
smm_lead = 4
# 2 Social Media Executives
emp7 = add_user('Henry Anderson', 'henry@agency.com',   'employee', team_id=2, department_id=2, manager_id=smm_lead)
emp8 = add_user('Isla Thomas',    'isla@agency.com',    'employee', team_id=2, department_id=2, manager_id=smm_lead)
print(f"  Social Media: Lead=Mike (id={smm_lead}), Henry (id={emp7}), Isla (id={emp8})")

# ── Web Development Dept (dept_id=3, team_id=2) ───────────
# Jane Developer already assigned to this dept (id=3), promote to team_lead
cursor.execute("UPDATE users SET role='team_lead' WHERE id=3")
conn.commit()
web_lead = 3
# 2 Developers
emp9  = add_user('Jack Martinez',  'jack@agency.com',   'employee', team_id=2, department_id=3, manager_id=web_lead)
emp10 = add_user('Karen Johnson',  'karen@agency.com',  'employee', team_id=2, department_id=3, manager_id=web_lead)
print(f"  Web Development: Lead=Jane (id={web_lead}), Jack (id={emp9}), Karen (id={emp10})")

cursor.close()
conn.close()
print("\nDone! Summary:")
print("  Marketing Team    → Lead: John | Employees: Alice, Bob")
print("  CRM Team          → Lead: Sarah | Employees: Carol, David")
print("  Video Editing     → Lead: Emma  | Employees: Frank, Grace")
print("  Social Media      → Lead: Mike  | Employees: Henry, Isla")
print("  Web Development   → Lead: Jane  | Employees: Jack, Karen")
print("\nAll passwords: password123")
