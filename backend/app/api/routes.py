"""
app/api/routes.py — All FastAPI route handlers combined
"""
from __future__ import annotations

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.models import Ticket, Team, Member, StatusEnum, PriorityEnum
from app.schemas.schemas import (
    TicketCreate, TicketUpdate, TicketOut, TicketListParams,
    TeamOut, TeamDetail, MemberOut,
    DashboardResponse, KPISummary, SLADashboard,
    AIChat, AIResponse, RouteRequest, RouteResponse,
    SLAPredictRequest, SLAPredictResponse, InsightItem
)
from app.services.services import TicketService, SLAService, DashboardService
from app.ai.routing_agent import route_ticket
from app.ai.sla_predictor import predict_sla_risk
from app.ai.rag_pipeline import rag_chat

logger = logging.getLogger(__name__)

# ── Routers ───────────────────────────────────────────────
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
ticket_router    = APIRouter(prefix="/api/tickets",   tags=["Tickets"])
team_router      = APIRouter(prefix="/api/teams",     tags=["Teams"])
ai_router        = APIRouter(prefix="/api/ai",        tags=["AI"])


# ════════════════════════════════════════════════════════
#  DASHBOARD ROUTES
# ════════════════════════════════════════════════════════

@dashboard_router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Full dashboard summary: KPIs + SLA + workload + recent tickets."""
    SLAService.check_and_update_breaches(db)
    kpis     = DashboardService.get_kpis(db)
    sla      = SLAService.get_sla_summary(db)
    workload = DashboardService.get_workload(db)

    recent_raw, _ = TicketService.list_tickets(
        db, TicketListParams(page=1, page_size=10, sort_by="created_at", sort_dir="desc")
    )
    recent = [TicketService.enrich_ticket_out(t) for t in recent_raw]

    return {"kpis": kpis, "sla": sla, "workload": workload, "recent_tickets": recent}


@dashboard_router.get("/kpis")
def get_kpis(db: Session = Depends(get_db)):
    return DashboardService.get_kpis(db)


@dashboard_router.get("/sla")
def get_sla(db: Session = Depends(get_db)):
    SLAService.check_and_update_breaches(db)
    return SLAService.get_sla_summary(db)


@dashboard_router.get("/workload")
def get_workload(db: Session = Depends(get_db)):
    return DashboardService.get_workload(db)


@dashboard_router.get("/trends")
def get_trends(days: int = 7, db: Session = Depends(get_db)):
    """Ticket volume trend for the last N days."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import cast, Date
    result = []
    today = datetime.now(timezone.utc).date()
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        new_count = db.query(func.count(Ticket.id)).filter(
            func.date(Ticket.created_at) == day
        ).scalar() or 0
        resolved_count = db.query(func.count(Ticket.id)).filter(
            Ticket.status == StatusEnum.resolved,
            func.date(Ticket.updated_at) == day
        ).scalar() or 0
        result.append({"date": str(day), "new": new_count, "resolved": resolved_count})
    return result


# ════════════════════════════════════════════════════════
#  TICKET ROUTES
# ════════════════════════════════════════════════════════

@ticket_router.get("")
def list_tickets(
    status:     Optional[str] = Query(None),
    team_id:    Optional[int] = Query(None),
    priority:   Optional[str] = Query(None),
    category:   Optional[str] = Query(None),
    assignee_id:Optional[int] = Query(None),
    search:     Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    sort_by:    str = Query("created_at"),
    sort_dir:   str = Query("desc"),
    page:       int = Query(1, ge=1),
    page_size:  int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    params = TicketListParams(
        status=status, team_id=team_id, priority=priority,
        category=category, assignee_id=assignee_id, search=search,
        date_from=date_from, date_to=date_to,
        sort_by=sort_by, sort_dir=sort_dir, page=page, page_size=page_size
    )
    tickets, total = TicketService.list_tickets(db, params)
    return {
        "total": total, "page": page, "page_size": page_size,
        "tickets": [TicketService.enrich_ticket_out(t) for t in tickets]
    }


@ticket_router.post("", status_code=201)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db)):
    """Create ticket — auto-routes to team, predicts SLA risk."""
    # 1. Route to team
    teams = db.query(Team).all()
    route = route_ticket(data.subject, data.description or "", data.category, teams)
    team  = db.query(Team).filter(Team.name == route["team_name"]).first()
    team_id = team.id if team else None

    # 2. Predict SLA risk
    sla_pred = predict_sla_risk(
        data.priority.value, data.category,
        route["team_name"], data.subject
    )

    # 3. Create
    ticket = TicketService.create_ticket(
        db, data,
        team_id=team_id,
        ai_confidence=route["confidence"],
        ai_reasoning=route["reasoning"],
        ai_sla_risk=sla_pred["breach_probability"]
    )

    enriched = TicketService.enrich_ticket_out(ticket)
    enriched["routing"] = route
    enriched["sla_prediction"] = sla_pred
    return enriched


@ticket_router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    return TicketService.enrich_ticket_out(ticket)


@ticket_router.patch("/{ticket_id}")
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db)):
    ticket = TicketService.update_ticket(db, ticket_id, data)
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    return TicketService.enrich_ticket_out(ticket)


@ticket_router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    db.delete(ticket)
    db.commit()


# ════════════════════════════════════════════════════════
#  TEAM ROUTES
# ════════════════════════════════════════════════════════

@team_router.get("")
def list_teams(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    result = []
    for t in teams:
        open_count = db.query(func.count(Ticket.id)).filter(
            Ticket.team_id == t.id,
            Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
        ).scalar() or 0
        resolved = db.query(func.count(Ticket.id)).filter(
            Ticket.team_id == t.id, Ticket.status == StatusEnum.resolved
        ).scalar() or 0
        sla_pct = SLAService.get_team_sla_percent(db, t.id)
        result.append({
            "id": t.id, "slug": t.slug, "name": t.name,
            "description": t.description, "domain": t.domain,
            "lead_name": t.lead_name, "color": t.color,
            "badge_color": t.badge_color, "sla_target": t.sla_target,
            "member_count": len(t.members),
            "open_tickets": open_count, "resolved_tickets": resolved,
            "sla_percent": sla_pct
        })
    return result


@team_router.get("/{team_id}/members")
def get_team_members(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(404, "Team not found")
    result = []
    for m in team.members:
        open_t = db.query(func.count(Ticket.id)).filter(
            Ticket.assignee_id == m.id,
            Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
        ).scalar() or 0
        resolved = db.query(func.count(Ticket.id)).filter(
            Ticket.assignee_id == m.id, Ticket.status == StatusEnum.resolved
        ).scalar() or 0
        resolved_tickets = db.query(Ticket).filter(
            Ticket.assignee_id == m.id, Ticket.status == StatusEnum.resolved
        ).all()
        from app.services.services import _avg_resolution
        met = sum(1 for t in resolved_tickets if t.sla_met is True)
        sla_pct = round(met / len(resolved_tickets) * 100, 1) if resolved_tickets else 0.0

        result.append({
            "id": m.id, "name": m.name, "role": m.role,
            "email": m.email, "initials": m.initials,
            "workload": m.workload, "team_id": m.team_id,
            "open_tickets": open_t, "resolved_tickets": resolved,
            "sla_percent": sla_pct
        })
    return result


@team_router.get("/{team_id}/tickets")
def get_team_tickets(
    team_id: int,
    status: Optional[str] = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
    db: Session = Depends(get_db)
):
    params = TicketListParams(team_id=team_id, status=status, page=page, page_size=page_size)
    tickets, total = TicketService.list_tickets(db, params)
    return {
        "total": total,
        "tickets": [TicketService.enrich_ticket_out(t) for t in tickets]
    }


@team_router.get("/{team_id}/members/{member_id}/tickets")
def get_member_tickets(
    team_id: int, member_id: int,
    page: int = Query(1), page_size: int = Query(10),
    db: Session = Depends(get_db)
):
    params = TicketListParams(assignee_id=member_id, page=page, page_size=page_size)
    tickets, total = TicketService.list_tickets(db, params)
    return {
        "total": total,
        "tickets": [TicketService.enrich_ticket_out(t) for t in tickets]
    }


# ════════════════════════════════════════════════════════
#  AI ROUTES
# ════════════════════════════════════════════════════════

@ai_router.post("/chat")
async def ai_chat(body: AIChat, db: Session = Depends(get_db)):
    """RAG-powered AI assistant with live project context."""
    kpis = DashboardService.get_kpis(db)
    history = [{"role": m.role, "content": m.content} for m in body.history]
    result = await rag_chat(body.message, history, live_context={"kpis": kpis})
    return result


@ai_router.post("/route")
def ai_route(body: RouteRequest, db: Session = Depends(get_db)):
    """AI ticket routing — returns recommended team with confidence."""
    teams = db.query(Team).all()
    result = route_ticket(body.subject, body.description or "", body.category, teams)
    team = db.query(Team).filter(Team.name == result["team_name"]).first()
    return {
        "recommended_team_id":   team.id if team else None,
        "recommended_team_name": result["team_name"],
        "confidence":            result["confidence"],
        "reasoning":             result["reasoning"],
        "alternative_teams":     result["alternative_teams"]
    }


@ai_router.post("/predict-sla")
def ai_predict_sla(body: SLAPredictRequest, db: Session = Depends(get_db)):
    """ML-based SLA breach prediction for a ticket."""
    result = predict_sla_risk(
        body.priority.value, body.category,
        body.team_name, body.subject
    )
    return result


@ai_router.get("/insights")
def ai_insights(db: Session = Depends(get_db)):
    """Auto-generated leadership insights based on current data."""
    SLAService.check_and_update_breaches(db)
    kpis     = DashboardService.get_kpis(db)
    sla_data = SLAService.get_sla_summary(db)
    insights = []

    # Insight: Infra team SLA alert
    for team in sla_data["team_breakdown"]:
        if team["sla_percent"] < 80:
            insights.append({
                "title": f"{team['team_name']} SLA Critical",
                "body": f"{team['team_name']} is at {team['sla_percent']}% SLA — well below the 95% target. Immediate review recommended.",
                "severity": "critical",
                "team": team["team_name"]
            })
        elif team["sla_percent"] < 90:
            insights.append({
                "title": f"{team['team_name']} SLA Below Target",
                "body": f"{team['team_name']} is at {team['sla_percent']}% SLA. Consider redistributing workload or adding resources.",
                "severity": "warning",
                "team": team["team_name"]
            })

    # Insight: active breaches
    if kpis["active_breaches"] > 10:
        insights.append({
            "title": "High SLA Breach Count",
            "body": f"{kpis['active_breaches']} tickets are currently in breach. Escalation to team leads is recommended.",
            "severity": "critical", "team": None
        })

    # Insight: resolution rate
    if kpis["resolution_rate"] >= 85:
        insights.append({
            "title": "Strong Resolution Rate",
            "body": f"Overall resolution rate is {kpis['resolution_rate']}% — above the 85% benchmark. Keep it up.",
            "severity": "info", "team": None
        })

    return insights
