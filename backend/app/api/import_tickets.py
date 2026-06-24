"""
app/api/import_tickets.py — Import tickets from Excel, CSV, PDF
Add this to ServicePulse backend
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone, timedelta
import io
import logging

from app.db.database import get_db
from app.models.models import Ticket, Team, Member, StatusEnum, PriorityEnum

logger = logging.getLogger(__name__)
import_router = APIRouter(prefix="/api/import", tags=["Import"])

SLA_HOURS = {'Critical': 4, 'High': 8, 'Medium': 24, 'Low': 72}

PRIORITY_MAP = {
    'critical': 'Critical', 'high': 'High', 'medium': 'Medium', 'low': 'Low',
    'p1': 'Critical', 'p2': 'High', 'p3': 'Medium', 'p4': 'Low',
    '1': 'Critical', '2': 'High', '3': 'Medium', '4': 'Low',
    'urgent': 'Critical', 'normal': 'Medium', 'moderate': 'Medium',
}

STATUS_MAP = {
    'open': 'Open', 'new': 'Open', 'active': 'Open',
    'in progress': 'In Progress', 'in-progress': 'In Progress', 'wip': 'In Progress',
    'pending': 'Pending', 'on hold': 'Pending', 'waiting': 'Pending',
    'resolved': 'Resolved', 'closed': 'Closed', 'done': 'Resolved', 'fixed': 'Resolved',
}

COL_MAP = {
    'subject':     ['subject', 'title', 'issue', 'summary', 'ticket_title', 'problem'],
    'description': ['description', 'details', 'body', 'notes', 'comments'],
    'category':    ['category', 'type', 'ticket_type', 'issue_type', 'service'],
    'priority':    ['priority', 'severity', 'urgency', 'impact'],
    'team':        ['team', 'team_name', 'department', 'group', 'assigned_team', 'support_group'],
    'assignee':    ['assignee', 'agent', 'assigned_to', 'owner', 'technician', 'engineer'],
    'reporter':    ['reporter', 'requester', 'raised_by', 'created_by', 'user', 'requestor'],
    'email':       ['email', 'reporter_email', 'requester_email', 'user_email', 'contact'],
    'status':      ['status', 'state', 'ticket_status', 'resolution_status'],
    'ticket_type': ['ticket_type', 'type', 'request_type', 'incident_type'],
}


def find_col(df_cols, targets):
    """Find the first matching column name."""
    for t in targets:
        if t in df_cols:
            return t
    return None


def normalize_df_row(row, df_cols) -> dict:
    """Normalize a DataFrame row to ticket dict."""
    def get(targets, default=''):
        col = find_col(df_cols, targets)
        val = str(row.get(col, default)).strip() if col else default
        return val if val and val.lower() != 'nan' else default

    priority = PRIORITY_MAP.get(get(COL_MAP['priority'], 'Medium').lower(), 'Medium')
    status   = STATUS_MAP.get(get(COL_MAP['status'], 'Open').lower(), 'Open')

    return {
        'subject':       get(COL_MAP['subject']),
        'description':   get(COL_MAP['description']),
        'category':      get(COL_MAP['category'], 'General'),
        'priority':      priority,
        'status':        status,
        'team_name':     get(COL_MAP['team']),
        'assignee_name': get(COL_MAP['assignee']),
        'reporter_name': get(COL_MAP['reporter']),
        'reporter_email':get(COL_MAP['email']),
        'ticket_type':   get(COL_MAP['ticket_type'], 'Incident'),
    }


def parse_excel_csv(contents: bytes, filename: str) -> List[dict]:
    try:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(contents)) if filename.endswith('.csv') else pd.read_excel(io.BytesIO(contents))
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        tickets = []
        for _, row in df.iterrows():
            t = normalize_df_row(row, list(df.columns))
            if t['subject']:
                tickets.append(t)
        return tickets
    except ImportError:
        raise HTTPException(500, "pandas not installed")
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")


def parse_pdf(contents: bytes) -> List[dict]:
    try:
        import pdfplumber
        tickets = []
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    headers = [str(h).strip().lower().replace(' ', '_') if h else f'col_{i}'
                               for i, h in enumerate(table[0])]
                    for row in table[1:]:
                        if not row:
                            continue
                        row_dict = {headers[i]: str(v).strip() if v else ''
                                    for i, v in enumerate(row) if i < len(headers)}
                        t = normalize_df_row(row_dict, headers)
                        if t['subject'] and t['subject'].lower() != 'nan':
                            tickets.append(t)
        return tickets
    except ImportError:
        raise HTTPException(500, "pdfplumber not installed")
    except Exception as e:
        raise HTTPException(400, f"Failed to parse PDF: {str(e)}")


def create_ticket_from_import(db: Session, data: dict, ticket_num: int) -> Ticket:
    """Create a ticket in the ServicePulse database from imported data."""
    ticket_number = f"SP-IMP-{ticket_num:04d}"

    # Find team
    team = None
    if data.get('team_name'):
        team = db.query(Team).filter(
            Team.name.ilike(f"%{data['team_name']}%")
        ).first()

    # Find assignee
    member = None
    if data.get('assignee_name'):
        member = db.query(Member).filter(
            Member.name.ilike(f"%{data['assignee_name']}%")
        ).first()
    elif team:
        # Auto-assign to team member with least tickets
        member = db.query(Member).filter(
            Member.team_id == team.id
        ).first()

    # SLA due date
    priority  = data.get('priority', 'Medium')
    hours     = SLA_HOURS.get(priority, 24)
    sla_due   = datetime.now(timezone.utc) + timedelta(hours=hours)

    # Map status
    status_enum_map = {
        'Open':        StatusEnum.open,
        'In Progress': StatusEnum.in_progress,
        'Pending':     StatusEnum.pending,
        'Resolved':    StatusEnum.resolved,
        'Closed':      StatusEnum.closed,
    }
    priority_enum_map = {
        'Critical': PriorityEnum.critical,
        'High':     PriorityEnum.high,
        'Medium':   PriorityEnum.medium,
        'Low':      PriorityEnum.low,
    }

    ticket = Ticket(
        ticket_number  = ticket_number,
        subject        = data['subject'][:255],
        description    = data.get('description', ''),
        category       = data.get('category', 'General'),
        priority       = priority_enum_map.get(priority, PriorityEnum.medium),
        status         = status_enum_map.get(data.get('status', 'Open'), StatusEnum.open),
        ticket_type    = data.get('ticket_type', 'Incident'),
        team_id        = team.id if team else None,
        member_id      = member.id if member else None,
        reporter_name  = data.get('reporter_name', 'Imported'),
        reporter_email = data.get('reporter_email', ''),
        sla_due_at     = sla_due,
        tags           = '["imported"]',
    )
    db.add(ticket)
    return ticket


# ── ENDPOINTS ─────────────────────────────────────────────

@import_router.post("/tickets")
async def import_tickets(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import tickets from Excel, CSV, or PDF file."""
    filename = file.filename.lower()
    contents = await file.read()

    if not contents:
        raise HTTPException(400, "Empty file uploaded")

    # Parse
    if filename.endswith(('.xlsx', '.xls')):
        tickets_data = parse_excel_csv(contents, filename)
        file_type = "Excel"
    elif filename.endswith('.csv'):
        tickets_data = parse_excel_csv(contents, filename)
        file_type = "CSV"
    elif filename.endswith('.pdf'):
        tickets_data = parse_pdf(contents)
        file_type = "PDF"
    else:
        raise HTTPException(400, "Unsupported file. Use .xlsx, .csv, or .pdf")

    if not tickets_data:
        raise HTTPException(400, "No valid ticket data found. Check column headers.")

    # Get current ticket count for numbering
    from sqlalchemy import func
    base_num = db.query(func.count(Ticket.id)).scalar() or 0

    created = []
    failed  = []

    for i, data in enumerate(tickets_data):
        try:
            ticket = create_ticket_from_import(db, data, base_num + i + 1)
            db.flush()
            created.append({
                "ticket_number": ticket.ticket_number,
                "subject":       data['subject'],
                "priority":      data.get('priority', 'Medium'),
                "team":          data.get('team_name', '—'),
            })
        except Exception as e:
            failed.append({"row": i + 2, "subject": data.get('subject', '?'), "reason": str(e)})

    if created:
        db.commit()
    
    logger.info(f"Imported {len(created)} tickets from {file_type} file")

    return {
        "status":        "success",
        "file_type":     file_type,
        "filename":      file.filename,
        "total_rows":    len(tickets_data),
        "created_count": len(created),
        "failed_count":  len(failed),
        "created":       created[:10],
        "failed":        failed[:5],
        "message":       f"Successfully imported {len(created)} tickets from {file_type}!"
    }


@import_router.get("/template")
async def download_template():
    """Download Excel template for ticket import."""
    try:
        import pandas as pd
        from fastapi.responses import StreamingResponse

        data = {
            'Subject':     ['Network connectivity issue in Block A', 'Laptop screen flickering', 'Unable to access VPN', 'Printer not working', 'Email not syncing'],
            'Category':    ['Network', 'Hardware', 'Network', 'Hardware', 'Software'],
            'Priority':    ['High', 'Medium', 'Critical', 'Low', 'Medium'],
            'Team':        ['Network Ops', 'Hardware', 'Network Ops', 'Hardware', 'Software'],
            'Description': ['Users cannot connect to internet', 'Screen flickers every 5 mins', 'VPN drops after 10 mins', 'Printer offline since morning', 'Outlook not receiving emails'],
            'Status':      ['Open', 'Open', 'Open', 'Open', 'Open'],
            'Reporter':    ['Ravi Kumar', 'Priya Singh', 'Arun Selvan', 'Deepa Nair', 'Karthik V'],
            'Email':       ['ravi@company.com', 'priya@company.com', 'arun@company.com', 'deepa@company.com', 'karthik@company.com'],
            'Ticket Type': ['Incident', 'Incident', 'Incident', 'Service Request', 'Incident'],
        }

        df  = pd.DataFrame(data)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tickets')
            # Auto-size columns
            ws = writer.sheets['Tickets']
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col) + 2
                ws.column_dimensions[col[0].column_letter].width = min(max_len, 40)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename=servicepulse_import_template.xlsx'}
        )
    except ImportError:
        raise HTTPException(500, "pandas/openpyxl not installed")
