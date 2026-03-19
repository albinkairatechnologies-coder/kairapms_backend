from app.utils.database import get_db_connection
from app.utils.timezone import now_ist, today_ist
from datetime import datetime, date
from decimal import Decimal
import json


def _s(row):
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (bytes, bytearray)):
            try:
                out[k] = json.loads(v)
            except Exception:
                out[k] = v.decode('utf-8', errors='replace')
        else:
            out[k] = v
    return out


class Proposal:

    @staticmethod
    def create(created_by: int, **kwargs):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        fields = ['created_by']
        values = [created_by]
        json_fields = {'requirements', 'form_data'}
        allowed = {
            'client_id', 'lead_name', 'company_name', 'email', 'phone',
            'project_type', 'project_description', 'budget_range', 'timeline',
            'requirements', 'priority', 'form_data', 'proposal_text', 'status',
        }
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                fields.append(k)
                values.append(json.dumps(v) if k in json_fields else v)
        placeholders = ', '.join(['%s'] * len(fields))
        cols = ', '.join(fields)
        cursor.execute(
            f"INSERT INTO proposals ({cols}) VALUES ({placeholders})", values
        )
        conn.commit()
        pid = cursor.lastrowid
        cursor.execute("""
            SELECT p.*, u.name AS created_by_name
            FROM proposals p
            JOIN users u ON p.created_by = u.id
            WHERE p.id = %s
        """, (pid,))
        row = _s(cursor.fetchone())
        cursor.close(); conn.close()
        return row

    @staticmethod
    def update(proposal_id: int, **kwargs):
        conn = get_db_connection()
        cursor = conn.cursor()
        json_fields = {'requirements', 'form_data'}
        allowed = {
            'lead_name', 'company_name', 'email', 'phone', 'project_type',
            'project_description', 'budget_range', 'timeline', 'requirements',
            'priority', 'form_data', 'proposal_text', 'status', 'client_id',
        }
        fields, values = [], []
        for k, v in kwargs.items():
            if k in allowed:
                fields.append(f"{k} = %s")
                values.append(json.dumps(v) if k in json_fields and v is not None else v)
        if not fields:
            cursor.close(); conn.close()
            return
        values.append(proposal_id)
        cursor.execute(f"UPDATE proposals SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()
        cursor.close(); conn.close()

    @staticmethod
    def get_by_id(proposal_id: int):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, u.name AS created_by_name, c.company_name AS client_company
            FROM proposals p
            JOIN users u ON p.created_by = u.id
            LEFT JOIN clients c ON p.client_id = c.id
            WHERE p.id = %s
        """, (proposal_id,))
        row = _s(cursor.fetchone())
        cursor.close(); conn.close()
        return row

    @staticmethod
    def get_all(created_by: int = None, status: str = None):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT p.*, u.name AS created_by_name, c.company_name AS client_company
            FROM proposals p
            JOIN users u ON p.created_by = u.id
            LEFT JOIN clients c ON p.client_id = c.id
            WHERE 1=1
        """
        params = []
        if created_by:
            query += " AND p.created_by = %s"; params.append(created_by)
        if status:
            query += " AND p.status = %s"; params.append(status)
        query += " ORDER BY p.created_at DESC"
        cursor.execute(query, params)
        rows = [_s(r) for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def delete(proposal_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proposals WHERE id = %s", (proposal_id,))
        conn.commit()
        cursor.close(); conn.close()

    @staticmethod
    def get_by_client(client_id: int):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, u.name AS created_by_name
            FROM proposals p
            JOIN users u ON p.created_by = u.id
            WHERE p.client_id = %s
            ORDER BY p.created_at DESC
        """, (client_id,))
        rows = [_s(r) for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def send(proposal_id: int, sent_by: int, note: str = None,
             template_id: str = None, template_name: str = None,
             line_items: list = None, total_amount: float = None):
        """Mark proposal as sent, store metadata, send email."""
        import smtplib, os
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from datetime import datetime

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT p.*, c.email AS client_email, c.contact_person,
                   c.company_name AS client_company
            FROM proposals p
            LEFT JOIN clients c ON p.client_id = c.id
            WHERE p.id = %s
        """, (proposal_id,))
        proposal = cursor.fetchone()
        if not proposal:
            cursor.close(); conn.close()
            return None, "Proposal not found"

        now = now_ist()
        cursor.execute("""
            UPDATE proposals
            SET status='sent', sent_at=%s, sent_by=%s, note=%s,
                template_id=%s, template_name=%s
            WHERE id=%s
        """, (now, sent_by, note, template_id, template_name, proposal_id))
        conn.commit()

        # Build email
        recipient = proposal.get('email') or proposal.get('client_email')
        if recipient:
            try:
                company_name = os.getenv('COMPANY_NAME', 'KairaFlow')
                company_email = os.getenv('COMPANY_EMAIL', 'info@kairaflow.com')
                smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
                smtp_port = int(os.getenv('SMTP_PORT', '587'))
                smtp_user = os.getenv('SMTP_USER', '')
                smtp_pass = os.getenv('SMTP_PASS', '')

                items_html = ''
                grand_total = total_amount or 0
                INR = '&#8377;'
                if line_items:
                    for item in line_items:
                        up = float(item.get('unit_price', 0))
                        tt = float(item.get('total', 0))
                        items_html += (
                            '<tr>'
                            f'<td style="padding:8px 12px;border-bottom:1px solid #f0f0f0">{item.get("description","")}</td>'
                            f'<td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center">{item.get("quantity",1)}</td>'
                            f'<td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right">{INR}{up:,.2f}</td>'
                            f'<td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right">{INR}{tt:,.2f}</td>'
                            '</tr>'
                        )

                html = f"""
                <div style="font-family:Inter,sans-serif;max-width:640px;margin:0 auto;background:#fff">
                  <div style="background:linear-gradient(135deg,#6366F1,#8B5CF6);padding:32px;text-align:center">
                    <h1 style="color:#fff;margin:0;font-size:28px">{company_name}</h1>
                    <p style="color:rgba(255,255,255,.8);margin:8px 0 0">Project Proposal</p>
                  </div>
                  <div style="padding:32px">
                    <p style="color:#374151">Dear <strong>{proposal.get('lead_name') or proposal.get('contact_person','')}</strong>,</p>
                    <p style="color:#374151">Thank you for your interest. Please find your project proposal below.</p>
                    <div style="background:#f9fafb;border-radius:12px;padding:20px;margin:20px 0">
                      <h3 style="margin:0 0 8px;color:#111">{template_name or 'Project Proposal'}</h3>
                      <p style="margin:0;color:#6b7280">Company: {proposal.get('company_name','')}</p>
                      <p style="margin:4px 0 0;color:#6b7280">Timeline: {proposal.get('timeline','TBD')}</p>
                    </div>
                    {f'<div style="background:#fffbeb;border-left:4px solid #F5C842;padding:16px;border-radius:8px;margin:16px 0"><p style="margin:0;color:#92400e">{note}</p></div>' if note else ''}
                    ('<h3 style="color:#111;margin:24px 0 12px">Investment Summary</h3><table style="width:100%;border-collapse:collapse"><thead><tr style="background:#f3f4f6"><th style="padding:10px 12px;text-align:left">Service</th><th style="padding:10px 12px;text-align:center">Qty</th><th style="padding:10px 12px;text-align:right">Unit Price</th><th style="padding:10px 12px;text-align:right">Total</th></tr></thead><tbody>' + items_html + f'</tbody><tfoot><tr><td colspan="3" style="padding:12px;text-align:right;font-weight:700">Total</td><td style="padding:12px;text-align:right;font-weight:700;color:#6366F1">{INR}{grand_total:,.2f}</td></tr></tfoot></table>' if line_items else '')
                    <div style="margin-top:32px;padding-top:24px;border-top:1px solid #e5e7eb;text-align:center">
                      <p style="color:#6b7280;font-size:14px">Questions? Reply to this email or contact us at {company_email}</p>
                    </div>
                  </div>
                </div>"""

                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"Project Proposal — {template_name or 'KairaFlow'}"
                msg['From']    = f"{company_name} <{smtp_user or company_email}>"
                msg['To']      = recipient
                msg.attach(MIMEText(html, 'html'))

                if smtp_user and smtp_pass:
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.sendmail(smtp_user, recipient, msg.as_string())
            except Exception as e:
                # Email failure is non-fatal — proposal is still marked sent
                print(f"Email send warning: {e}")

        cursor.execute("SELECT * FROM proposals WHERE id=%s", (proposal_id,))
        row = _s(cursor.fetchone())
        cursor.close(); conn.close()
        return row, None

    @staticmethod
    def mark_viewed(proposal_id: int):
        from datetime import datetime
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE proposals SET status='viewed', viewed_at=%s
            WHERE id=%s AND status='sent'
        """, (now_ist(), proposal_id))
        conn.commit()
        cursor.close(); conn.close()


class Invoice:

    @staticmethod
    def _next_number():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM invoices")
        count = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return f"INV-{today_ist().year}-{str(count + 1).zfill(4)}"

    @staticmethod
    def create(created_by: int, **kwargs):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        invoice_number = kwargs.get('invoice_number') or Invoice._next_number()
        json_fields = {'billed_to', 'billed_by', 'line_items'}
        fields = ['created_by', 'invoice_number']
        values = [created_by, invoice_number]
        allowed = {
            'proposal_id', 'client_id', 'invoice_date', 'due_date',
            'billed_to', 'billed_by', 'line_items', 'subtotal',
            'tax_percent', 'tax_amount', 'total_amount',
            'payment_terms', 'notes', 'status', 'email_body',
        }
        for k, v in kwargs.items():
            if k in allowed and v is not None and k != 'invoice_number':
                fields.append(k)
                values.append(json.dumps(v) if k in json_fields else v)
        placeholders = ', '.join(['%s'] * len(fields))
        cols = ', '.join(fields)
        cursor.execute(
            f"INSERT INTO invoices ({cols}) VALUES ({placeholders})", values
        )
        conn.commit()
        iid = cursor.lastrowid
        cursor.execute("""
            SELECT i.*, u.name AS created_by_name
            FROM invoices i
            JOIN users u ON i.created_by = u.id
            WHERE i.id = %s
        """, (iid,))
        row = _s(cursor.fetchone())
        cursor.close(); conn.close()
        return row

    @staticmethod
    def update(invoice_id: int, **kwargs):
        conn = get_db_connection()
        cursor = conn.cursor()
        json_fields = {'billed_to', 'billed_by', 'line_items'}
        allowed = {
            'invoice_date', 'due_date', 'billed_to', 'billed_by', 'line_items',
            'subtotal', 'tax_percent', 'tax_amount', 'total_amount',
            'payment_terms', 'notes', 'status', 'email_body',
        }
        fields, values = [], []
        for k, v in kwargs.items():
            if k in allowed:
                fields.append(f"{k} = %s")
                values.append(json.dumps(v) if k in json_fields and v is not None else v)
        if not fields:
            cursor.close(); conn.close()
            return
        values.append(invoice_id)
        cursor.execute(f"UPDATE invoices SET {', '.join(fields)} WHERE id = %s", values)
        conn.commit()
        cursor.close(); conn.close()

    @staticmethod
    def get_by_id(invoice_id: int):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.*, u.name AS created_by_name
            FROM invoices i
            JOIN users u ON i.created_by = u.id
            WHERE i.id = %s
        """, (invoice_id,))
        row = _s(cursor.fetchone())
        cursor.close(); conn.close()
        return row

    @staticmethod
    def get_all(created_by: int = None, status: str = None, client_id: int = None):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT i.*, u.name AS created_by_name
            FROM invoices i
            JOIN users u ON i.created_by = u.id
            WHERE 1=1
        """
        params = []
        if created_by:
            query += " AND i.created_by = %s"; params.append(created_by)
        if status:
            query += " AND i.status = %s"; params.append(status)
        if client_id:
            query += " AND i.client_id = %s"; params.append(client_id)
        query += " ORDER BY i.created_at DESC"
        cursor.execute(query, params)
        rows = [_s(r) for r in cursor.fetchall()]
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def delete(invoice_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
        conn.commit()
        cursor.close(); conn.close()
