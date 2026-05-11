"""
app/services/services.py — Business logic layer
Separates DB operations from API route handlers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, List
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, and_, or_

from app.models.models import (
    Ticket, Team, Member, SLARule,
    PriorityEnum, StatusEnum
)
from app.schemas.schemas import TicketCreate, TicketUpdate, TicketListParams

logger = logging.getLogger(__name__)

# ── SLA hours per priority ─────────────────────────────────
SLA_RESOLUTION_HOURS = {
    PriorityEnum.critical: 4,
    PriorityEnum.high:     8,
    PriorityEnum.medium:   24,
    PriorityEnum.low:      72,
}


# ════════════════════════════════════════════════════════
#  TICKET SERVICE
# ════════════════════════════════════════════════════════

class TicketService:

    @staticmethod
    def generate_ticket_number(db: Session) -> str:
        count = db.query(func.count(Ticket.id)).scalar() or 0
        return f"TK-{1000 + count + 1}"

    @staticmethod
    def get_sla_due(priority: PriorityEnum, created_at: datetime) -> datetime:
        hours = SLA_RESOLUTION_HOURS.get(priority, 24)
        return created_at + timedelta(hours=hours)

    @staticmethod
    def create_ticket(
        db: Session,
        data: TicketCreate,
        team_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        ai_confidence: Optional[float] = None,
        ai_reasoning: Optional[str] = None,
        ai_sla_risk: Optional[float] = None,
    ) -> Ticket:
        now = datetime.now(timezone.utc)
        ticket = Ticket(
            ticket_number=TicketService.generate_ticket_number(db),
            subject=data.subject,
            description=data.description,
            category=data.category,
            priority=data.priority,
            status=StatusEnum.open,
            ticket_type=data.ticket_type,
            reporter_name=data.reporter_name,
            reporter_email=data.reporter_email,
            reporter_phone=data.reporter_phone,
            tags=data.tags,
            team_id=team_id,
            assignee_id=assignee_id,
            created_at=now,
            updated_at=now,
            sla_due_at=TicketService.get_sla_due(data.priority, now),
            embedding_text=f"{data.subject} {data.description or ''} {data.category}",
            ai_routing_confidence=ai_confidence,
            ai_routing_reason=ai_reasoning,
            ai_predicted_sla_risk=ai_sla_risk,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def update_ticket(db: Session, ticket_id: int, data: TicketUpdate) -> Optional[Ticket]:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(ticket, field, value)
        ticket.updated_at = datetime.now(timezone.utc)
        if data.status == StatusEnum.resolved and not ticket.resolved_at:
            ticket.resolved_at = datetime.now(timezone.utc)
            ticket.sla_met = ticket.resolved_at <= ticket.sla_due_at if ticket.sla_due_at else None
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def list_tickets(db: Session, params: TicketListParams) -> tuple[List[Ticket], int]:
        q = db.query(Ticket)

        if params.status:
            q = q.filter(Ticket.status == params.status)
        if params.team_id:
            q = q.filter(Ticket.team_id == params.team_id)
        if params.priority:
            q = q.filter(Ticket.priority == params.priority)
        if params.category:
            q = q.filter(Ticket.category == params.category)
        if params.assignee_id:
            q = q.filter(Ticket.assignee_id == params.assignee_id)
        if params.search:
            term = f"%{params.search}%"
            q = q.filter(or_(
                Ticket.subject.ilike(term),
                Ticket.ticket_number.ilike(term),
                Ticket.reporter_name.ilike(term),
            ))
        if params.date_from:
            q = q.filter(Ticket.created_at >= params.date_from)
        if params.date_to:
            q = q.filter(Ticket.created_at <= params.date_to + " 23:59:59")

        total = q.count()

        sort_col = getattr(Ticket, params.sort_by, Ticket.created_at)
        q = q.order_by(desc(sort_col) if params.sort_dir == "desc" else asc(sort_col))
        q = q.offset((params.page - 1) * params.page_size).limit(params.page_size)

        return q.all(), total

    @staticmethod
    def enrich_ticket_out(ticket: Ticket) -> dict:
        """Add team_name and assignee_name to ticket data."""
        data = {c.name: getattr(ticket, c.name) for c in ticket.__table__.columns}
        data["team_name"]     = ticket.team.name     if ticket.team     else None
        data["assignee_name"] = ticket.assignee.name if ticket.assignee else None
        return data


# ════════════════════════════════════════════════════════
#  SLA SERVICE
# ════════════════════════════════════════════════════════

class SLAService:

    @staticmethod
    def check_and_update_breaches(db: Session) -> int:
        """Scan open tickets and mark SLA breaches. Returns count updated."""
        now = datetime.now(timezone.utc)
        overdue = db.query(Ticket).filter(
            Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress]),
            Ticket.sla_due_at < now,
            Ticket.status != StatusEnum.sla_breach
        ).all()

        for t in overdue:
            t.status = StatusEnum.sla_breach
            t.sla_met = False
            t.sla_breach_at = now
            if t.sla_due_at:
                delta = now - t.sla_due_at
                t.sla_breach_minutes = delta.total_seconds() / 60

        db.commit()
        return len(overdue)

    @staticmethod
    def get_team_sla_percent(db: Session, team_id: int) -> float:
        resolved = db.query(Ticket).filter(
            Ticket.team_id == team_id,
            Ticket.status == StatusEnum.resolved,
        ).all()
        if not resolved:
            return 0.0
        met = sum(1 for t in resolved if t.sla_met is True)
        return round(met / len(resolved) * 100, 1)

    @staticmethod
    def get_sla_summary(db: Session) -> dict:
        teams = db.query(Team).all()
        breakdown = []
        for team in teams:
            resolved = db.query(Ticket).filter(
                Ticket.team_id == team.id,
                Ticket.status == StatusEnum.resolved
            ).all()
            met = sum(1 for t in resolved if t.sla_met is True)
            sla_pct = round(met / len(resolved) * 100, 1) if resolved else 0.0
            breaches = db.query(func.count(Ticket.id)).filter(
                Ticket.team_id == team.id,
                Ticket.status == StatusEnum.sla_breach
            ).scalar()
            avg_res = _avg_resolution(resolved)
            breakdown.append({
                "team_id": team.id, "team_name": team.name,
                "sla_percent": sla_pct, "open": _count_open(db, team.id),
                "resolved": len(resolved), "active_breaches": breaches or 0,
                "avg_resolution_hours": avg_res
            })

        all_resolved = db.query(Ticket).filter(Ticket.status == StatusEnum.resolved).all()
        overall_met = sum(1 for t in all_resolved if t.sla_met is True)
        overall = round(overall_met / len(all_resolved) * 100, 1) if all_resolved else 0.0

        return {
            "overall_sla": overall,
            "target": 95.0,
            "active_breaches": db.query(func.count(Ticket.id)).filter(
                Ticket.status == StatusEnum.sla_breach).scalar() or 0,
            "avg_resolution_hours": _avg_resolution(all_resolved),
            "team_breakdown": breakdown,
            "monthly_trend": _mock_monthly_trend(overall)
        }


# ════════════════════════════════════════════════════════
#  DASHBOARD SERVICE
# ════════════════════════════════════════════════════════

class DashboardService:

    @staticmethod
    def get_kpis(db: Session) -> dict:
        total     = db.query(func.count(Ticket.id)).scalar() or 0
        resolved  = db.query(func.count(Ticket.id)).filter(Ticket.status == StatusEnum.resolved).scalar() or 0
        open_t    = db.query(func.count(Ticket.id)).filter(Ticket.status == StatusEnum.open).scalar() or 0
        inprog    = db.query(func.count(Ticket.id)).filter(Ticket.status == StatusEnum.in_progress).scalar() or 0
        breaches  = db.query(func.count(Ticket.id)).filter(Ticket.status == StatusEnum.sla_breach).scalar() or 0
        engineers = db.query(func.count(Member.id)).filter(Member.is_active == True).scalar() or 0

        all_resolved = db.query(Ticket).filter(Ticket.status == StatusEnum.resolved).all()
        met = sum(1 for t in all_resolved if t.sla_met is True)
        sla_pct = round(met / len(all_resolved) * 100, 1) if all_resolved else 0.0
        res_rate = round(resolved / total * 100, 1) if total else 0.0

        return {
            "total_tickets": total, "resolved": resolved,
            "resolution_rate": res_rate, "open_tickets": open_t,
            "in_progress": inprog, "sla_met_percent": sla_pct,
            "active_breaches": breaches,
            "avg_resolution_hours": _avg_resolution(all_resolved),
            "csat_score": 4.3,   # Would come from a ratings table in a real system
            "active_engineers": engineers
        }

    @staticmethod
    def get_workload(db: Session) -> list[dict]:
        teams = db.query(Team).all()
        result = []
        for team in teams:
            open_t = _count_open(db, team.id)
            member_count = db.query(func.count(Member.id)).filter(Member.team_id == team.id).scalar() or 1
            overloaded = sum(
                1 for m in team.members
                if db.query(func.count(Ticket.id)).filter(
                    Ticket.assignee_id == m.id,
                    Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
                ).scalar() >= 10
            )
            result.append({
                "team_id": team.id, "team_name": team.name,
                "open_tickets": open_t, "member_count": member_count,
                "avg_per_member": round(open_t / member_count, 1),
                "overloaded_count": overloaded
            })
        return result


# ── Helpers ───────────────────────────────────────────────

def _count_open(db: Session, team_id: int) -> int:
    return db.query(func.count(Ticket.id)).filter(
        Ticket.team_id == team_id,
        Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
    ).scalar() or 0


def _avg_resolution(tickets: List[Ticket]) -> float:
    durations = []
    for t in tickets:
        if t.resolved_at and t.created_at:
            hours = (t.resolved_at - t.created_at).total_seconds() / 3600
            durations.append(hours)
    return round(sum(durations) / len(durations), 1) if durations else 0.0


def _mock_monthly_trend(current_sla: float) -> list[dict]:
    months = ["Dec 25","Jan 26","Feb 26","Mar 26","Apr 26","May 26"]
    vals   = [88, 90, 91, 89, 93, current_sla or 92]
    return [{"month": m, "sla": v, "target": 95} for m, v in zip(months, vals)]
