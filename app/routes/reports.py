from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models.other import WorkLog, CompanySettings
from app.models.user import User
import io, csv, os
from datetime import datetime

reports_bp = Blueprint('reports', __name__)

ADMIN_ROLES = ['admin', 'team_lead', 'marketing_head', 'crm']


def _serialize(rows):
    """Convert timedelta/date objects to strings for JSON."""
    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if hasattr(v, 'total_seconds'):  # timedelta (TIME columns)
                total = int(v.total_seconds())
                clean[k] = f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
            elif hasattr(v, 'isoformat'):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        result.append(clean)
    return result


@reports_bp.route('/reports/client-summary', methods=['GET'])
@jwt_required()
def report_client_summary():
    claims = get_jwt()
    if claims['role'] not in ADMIN_ROLES:
        return jsonify({"error": "Unauthorized"}), 403
    client_id = request.args.get('client_id')
    if not client_id:
        return jsonify({"error": "client_id required"}), 400
    data = WorkLog.get_client_summary(
        int(client_id),
        request.args.get('start_date'),
        request.args.get('end_date')
    )
    # Serialize nested dicts
    for key in ['by_department', 'by_task', 'by_employee', 'daily_timeline']:
        data[key] = _serialize(data[key])
    if data.get('overall'):
        data['overall'] = _serialize([data['overall']])[0]
    return jsonify(data), 200


@reports_bp.route('/reports/department', methods=['GET'])
@jwt_required()
def report_department():
    claims = get_jwt()
    if claims['role'] not in ADMIN_ROLES:
        return jsonify({"error": "Unauthorized"}), 403
    rows = WorkLog.get_department_summary(
        department=request.args.get('department'),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date')
    )
    return jsonify(_serialize(rows)), 200


@reports_bp.route('/reports/employee', methods=['GET'])
@jwt_required()
def report_employee():
    claims = get_jwt()
    if claims['role'] not in ADMIN_ROLES:
        return jsonify({"error": "Unauthorized"}), 403
    employee_id = request.args.get('employee_id')
    if not employee_id:
        return jsonify({"error": "employee_id required"}), 400
    rows = WorkLog.get_employee_summary(
        int(employee_id),
        request.args.get('start_date'),
        request.args.get('end_date')
    )
    return jsonify(_serialize(rows)), 200


@reports_bp.route('/reports/full', methods=['GET'])
@jwt_required()
def report_full():
    claims = get_jwt()
    if claims['role'] not in ADMIN_ROLES:
        return jsonify({"error": "Unauthorized"}), 403
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date required"}), 400
    rows = WorkLog.get_full_company_summary(start_date, end_date)
    return jsonify(_serialize(rows)), 200


@reports_bp.route('/reports/export-csv', methods=['POST'])
@jwt_required()
def export_csv():
    claims = get_jwt()
    if claims['role'] not in ADMIN_ROLES:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    rows = data.get('rows', [])
    report_type = data.get('report_type', 'report')
    if not rows:
        return jsonify({"error": "No data"}), 400

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={report_type}_{datetime.now().strftime("%Y%m%d")}.csv'
    return response


@reports_bp.route('/reports/generate-pdf', methods=['POST'])
@jwt_required()
def generate_pdf():
    claims = get_jwt()
    user_id = int(get_jwt_identity())
    if claims['role'] not in ADMIN_ROLES:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    rows = data.get('rows', [])
    report_type = data.get('report_type', 'Work Summary Report')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    columns = data.get('columns', [])
    totals = data.get('totals', {})

    generator = User.get_by_id(user_id)
    generator_name = generator['name'] if generator else 'Admin'

    COL_LABELS = {
        'user_name': 'Employee', 'department_name': 'Department', 'task_title': 'Task',
        'log_date': 'Date', 'work_date': 'Date', 'start_time': 'Start', 'end_time': 'End',
        'duration_minutes': 'Duration', 'hours_worked': 'Hours', 'status': 'Status',
        'company_name': 'Client', 'team_name': 'Team', 'employee_name': 'Employee',
        'department': 'Department',
    }

    def img_path(filename):
        return os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'frontend', filename)
        )

    top_path    = img_path('letterpadtop.png')
    bottom_path = img_path('letterpadbottom.png')

    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Image, Table, TableStyle, Spacer, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from PIL import Image as PILImage

    PAGE_W, PAGE_H = A4

    def img_dims(path):
        """Return (width_pts, height_pts) scaled to full page width."""
        pil = PILImage.open(path)
        iw, ih = pil.size
        h = PAGE_W * (ih / iw)
        return PAGE_W, h

    top_w,    top_h    = img_dims(top_path)    if os.path.exists(top_path)    else (0, 0)
    bottom_w, bottom_h = img_dims(bottom_path) if os.path.exists(bottom_path) else (0, 0)

    # ── Build table data ──
    header_row = [COL_LABELS.get(c, c.replace('_', ' ').title()) for c in columns]
    table_data = [header_row]
    for row in rows:
        table_data.append([str(row.get(c, '') or '') for c in columns])
    if totals:
        table_data.append([str(totals.get(c, '') or '') for c in columns])

    col_count = len(columns) or 1

    title_style  = ParagraphStyle('t', fontSize=13, textColor=colors.HexColor('#2563eb'),
                                   spaceAfter=2, fontName='Helvetica-Bold')
    sub_style    = ParagraphStyle('s', fontSize=9,  textColor=colors.HexColor('#555555'),
                                   spaceAfter=4, fontName='Helvetica')
    footer_style = ParagraphStyle('f', fontSize=8,  textColor=colors.HexColor('#888888'),
                                   fontName='Helvetica')

    SIDE_PAD = 14 * mm
    inner_w  = PAGE_W - 2 * SIDE_PAD
    col_w    = inner_w / col_count

    tbl = Table(table_data, colWidths=[col_w] * col_count, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0),  (-1, 0),  colors.HexColor('#dbeafe')),
        ('TEXTCOLOR',      (0, 0),  (-1, 0),  colors.HexColor('#1e3a8a')),
        ('FONTNAME',       (0, 0),  (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0),  (-1, 0),  8),
        ('TOPPADDING',     (0, 0),  (-1, 0),  5),
        ('BOTTOMPADDING',  (0, 0),  (-1, 0),  5),
        ('FONTNAME',       (0, 1),  (-1, -2), 'Helvetica'),
        ('FONTSIZE',       (0, 1),  (-1, -2), 7.5),
        ('ROWBACKGROUNDS', (0, 1),  (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
        ('TOPPADDING',     (0, 1),  (-1, -2), 4),
        ('BOTTOMPADDING',  (0, 1),  (-1, -2), 4),
        ('BACKGROUND',     (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('FONTNAME',       (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',       (0, -1), (-1, -1), 8),
        ('GRID',           (0, 0),  (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('VALIGN',         (0, 0),  (-1, -1), 'MIDDLE'),
    ]))

    def build_elements():
        elems = [
            Paragraph(report_type, title_style),
            Paragraph(f'Date Range: {start_date}  to  {end_date}', sub_style),
            Spacer(1, 4 * mm),
            tbl,
            Spacer(1, 5 * mm),
            Paragraph(
                f'Generated by: {generator_name} &nbsp;&nbsp;&nbsp; '
                f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                footer_style
            ),
        ]
        # Wrap with side padding
        wrapper = Table([[ elems ]], colWidths=[inner_w])
        wrapper.setStyle(TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), SIDE_PAD),
            ('RIGHTPADDING',  (0, 0), (-1, -1), SIDE_PAD),
            ('TOPPADDING',    (0, 0), (-1, -1), 5 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4 * mm),
        ]))
        return [wrapper]

    # Top image drawn on every page via callback
    def on_page(canvas, doc):
        canvas.saveState()
        if os.path.exists(top_path) and top_h > 0:
            canvas.drawImage(top_path, 0, PAGE_H - top_h,
                             width=PAGE_W, height=top_h,
                             preserveAspectRatio=True, mask='auto')
        canvas.restoreState()

    # Bottom image as last flowable — always at end of content
    def all_elements():
        elems = build_elements()
        if os.path.exists(bottom_path) and bottom_h > 0:
            elems.append(Spacer(1, 4 * mm))
            elems.append(Image(bottom_path, width=PAGE_W, height=bottom_h))
        return elems

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=0, rightMargin=0,
        topMargin=top_h, bottomMargin=0,
    )
    doc.build(all_elements(), onFirstPage=on_page, onLaterPages=on_page)

    buf.seek(0)
    response = make_response(buf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        f'attachment; filename={report_type.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
    )
    return response
