"""
app/api/ai_enhanced.py — Enhanced AI Features for ServicePulse
1. AI Daily Briefing
2. AI Ticket Summarizer
3. AI Performance Coach
4. AI Anomaly Detector
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import logging

from app.db.database import get_db
from app.services.services import DashboardService, SLAService
from app.ai.rag_pipeline import rag_chat

logger = logging.getLogger(__name__)
ai_enhanced_router = APIRouter(prefix="/api/ai", tags=["AI Enhanced"])


# ── Schemas ───────────────────────────────────────────────

class TicketSummarizeRequest(BaseModel):
    ticket_id: int
    subject: str
    description: Optional[str] = None
    category: Optional[str] = None
    priority: str = "Medium"
    status: str = "Open"
    team_name: Optional[str] = None
    assignee_name: Optional[str] = None
    created_at: Optional[str] = None
    sla_due_at: Optional[str] = None

class PerformanceCoachRequest(BaseModel):
    team_id: Optional[int] = None

class AnomalyRequest(BaseModel):
    lookback_hours: int = 24


# ── 1. AI DAILY BRIEFING ──────────────────────────────────

@ai_enhanced_router.get("/daily-briefing")
async def get_daily_briefing(db: Session = Depends(get_db)):
    """
    Auto-generates a leadership briefing with:
    - Yesterday's performance summary
    - Today's SLA risks
    - Team highlights
    - Action items
    """
    kpis     = DashboardService.get_kpis(db)
    sla_data = SLAService.get_sla_summary(db)
    workload = DashboardService.get_workload(db)
    now      = datetime.now(timezone.utc)

    # Build context for AI
    team_issues = [t for t in sla_data["team_breakdown"] if t["sla_percent"] < 90]
    overloaded  = [t for t in workload if t["overloaded_count"] > 0]

    prompt = f"""Generate a concise executive daily briefing for IT leadership.

TODAY: {now.strftime('%A, %d %B %Y')}

CURRENT METRICS:
- Total tickets: {kpis['total_tickets']} | Resolved: {kpis['resolved']} ({kpis['resolution_rate']}%)
- Overall SLA: {kpis['sla_met_percent']}% (target: 95%)
- Active SLA breaches: {kpis['active_breaches']}
- Open tickets: {kpis['open_tickets']} | In Progress: {kpis['in_progress']}
- CSAT Score: {kpis['csat_score']}/5
- Active engineers: {kpis['active_engineers']} across 7 teams

TEAMS BELOW 90% SLA: {', '.join([t['team_name'] + ' (' + str(t['sla_percent']) + '%)' for t in team_issues]) or 'None — all teams performing well'}

OVERLOADED TEAMS: {', '.join([t['team_name'] for t in overloaded]) or 'None'}

Generate a professional briefing with these sections:
1. **Executive Summary** (2-3 sentences)
2. **Key Wins** (what went well)
3. **Areas of Concern** (specific issues needing attention)
4. **Action Items** (3-5 specific actions for today)
5. **SLA Risk Alert** (teams/tickets at risk)

Keep it concise, data-driven, and actionable. Use bullet points."""

    result = await rag_chat(prompt, [], live_context={"kpis": kpis})

    return {
        "generated_at": now.isoformat(),
        "date":         now.strftime('%A, %d %B %Y'),
        "briefing":     result["reply"],
        "kpis":         kpis,
        "alerts": {
            "sla_breach_count":  kpis["active_breaches"],
            "teams_at_risk":     [t["team_name"] for t in team_issues],
            "overloaded_teams":  [t["team_name"] for t in overloaded],
        }
    }


# ── 2. AI TICKET SUMMARIZER ───────────────────────────────

@ai_enhanced_router.post("/summarize-ticket")
async def summarize_ticket(data: TicketSummarizeRequest, db: Session = Depends(get_db)):
    """
    Summarizes a ticket with:
    - Root cause analysis
    - Impact assessment
    - Suggested resolution steps
    - Estimated resolution time
    """
    prompt = f"""Analyze this IT support ticket and provide a structured summary.

TICKET DETAILS:
- ID: #{data.ticket_id}
- Subject: {data.subject}
- Description: {data.description or 'No description provided'}
- Category: {data.category or 'Unknown'}
- Priority: {data.priority}
- Status: {data.status}
- Team: {data.team_name or 'Unassigned'}
- Assignee: {data.assignee_name or 'Unassigned'}
- Created: {data.created_at or 'Unknown'}
- SLA Due: {data.sla_due_at or 'Unknown'}

Provide a structured analysis with:
1. **Issue Summary** (1-2 sentences — plain English for executives)
2. **Root Cause Analysis** (likely technical cause)
3. **Business Impact** (who/what is affected and how severely)
4. **Recommended Resolution Steps** (numbered, specific steps)
5. **Estimated Resolution Time** (based on priority and category)
6. **Escalation Required?** (Yes/No with reason)

Be specific and technical where appropriate. Keep executive summary simple."""

    result = await rag_chat(prompt, [], live_context=None)

    return {
        "ticket_id":    data.ticket_id,
        "subject":      data.subject,
        "priority":     data.priority,
        "status":       data.status,
        "summary":      result["reply"],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


# ── 3. AI PERFORMANCE COACH ───────────────────────────────

@ai_enhanced_router.get("/performance-coach")
async def performance_coach(db: Session = Depends(get_db)):
    """
    Analyzes team/engineer performance and provides coaching recommendations:
    - Identifies struggling engineers
    - Suggests workload redistribution
    - Flags burnout risks
    - Recommends training needs
    """
    from app.models.models import Team, Member, Ticket, StatusEnum
    from sqlalchemy import func

    teams   = db.query(Team).all()
    kpis    = DashboardService.get_kpis(db)
    workload = DashboardService.get_workload(db)

    # Build team performance data
    team_data = []
    for team in teams:
        open_t = db.query(func.count(Ticket.id)).filter(
            Ticket.team_id == team.id,
            Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
        ).scalar() or 0

        resolved = db.query(func.count(Ticket.id)).filter(
            Ticket.team_id == team.id,
            Ticket.status == StatusEnum.resolved
        ).scalar() or 0

        breaches = db.query(func.count(Ticket.id)).filter(
            Ticket.team_id == team.id,
            Ticket.status == StatusEnum.sla_breach
        ).scalar() or 0

        members = len(team.members)
        avg_load = round(open_t / members, 1) if members > 0 else 0

        team_data.append({
            "name":     team.name,
            "lead":     team.lead_name,
            "members":  members,
            "open":     open_t,
            "resolved": resolved,
            "breaches": breaches,
            "avg_load": avg_load,
            "sla_target": team.sla_target
        })

    team_summary = "\n".join([
        f"- {t['name']}: {t['members']} engineers, {t['open']} open, "
        f"{t['resolved']} resolved, {t['breaches']} breaches, "
        f"{t['avg_load']} avg tickets/person (Lead: {t['lead']})"
        for t in team_data
    ])

    prompt = f"""Act as an IT Performance Coach for a leadership team.

PROJECT ATLAS TEAM METRICS:
{team_summary}

OVERALL:
- Total tickets: {kpis['total_tickets']}
- Resolution rate: {kpis['resolution_rate']}%
- SLA compliance: {kpis['sla_met_percent']}%
- Active engineers: {kpis['active_engineers']}

Provide a Performance Coaching Report with:
1. **Overall Team Health** (traffic light rating: 🟢/🟡/🔴 per team)
2. **Top Performers** (teams/individuals excelling — be specific)
3. **Teams Needing Support** (specific issues and root causes)
4. **Burnout Risk Assessment** (who may be overloaded)
5. **Workload Redistribution Recommendations** (specific actions)
6. **Training & Development Suggestions** (skill gaps identified)
7. **This Week's Priority Actions** (top 3 things leadership should do)

Be specific, empathetic, and constructive. Focus on actionable improvements."""

    result = await rag_chat(prompt, [], live_context={"kpis": kpis})

    return {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "team_metrics":  team_data,
        "coaching_report": result["reply"],
        "summary": {
            "total_teams":      len(team_data),
            "teams_at_risk":    len([t for t in team_data if t["breaches"] > 0]),
            "avg_load_overall": round(sum(t["avg_load"] for t in team_data) / len(team_data), 1) if team_data else 0,
        }
    }


# ── 4. AI ANOMALY DETECTOR ────────────────────────────────

@ai_enhanced_router.get("/anomalies")
async def detect_anomalies(db: Session = Depends(get_db)):
    """
    Detects unusual patterns in ticket data:
    - Sudden spikes in ticket volume
    - SLA breach clusters
    - Unusual category patterns
    - Engineer performance drops
    """
    from app.models.models import Ticket, StatusEnum, PriorityEnum
    from sqlalchemy import func

    now     = datetime.now(timezone.utc)
    kpis    = DashboardService.get_kpis(db)
    sla     = SLAService.get_sla_summary(db)

    # Count tickets by priority
    critical_count = db.query(func.count(Ticket.id)).filter(
        Ticket.priority == PriorityEnum.critical,
        Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
    ).scalar() or 0

    high_count = db.query(func.count(Ticket.id)).filter(
        Ticket.priority == PriorityEnum.high,
        Ticket.status.in_([StatusEnum.open, StatusEnum.in_progress])
    ).scalar() or 0

    breach_count = kpis["active_breaches"]
    open_count   = kpis["open_tickets"]

    # Build anomaly context
    anomalies_found = []

    if breach_count > 10:
        anomalies_found.append(f"HIGH: {breach_count} active SLA breaches detected (threshold: 10)")
    if critical_count > 3:
        anomalies_found.append(f"CRITICAL: {critical_count} critical priority tickets open simultaneously")
    if high_count > 15:
        anomalies_found.append(f"WARNING: Unusual spike in High priority tickets ({high_count})")

    teams_below_80 = [t for t in sla["team_breakdown"] if t["sla_percent"] < 80]
    for team in teams_below_80:
        anomalies_found.append(f"ALERT: {team['team_name']} SLA critically low at {team['sla_percent']}%")

    prompt = f"""Analyze these IT service desk metrics for anomalies and unusual patterns.

CURRENT STATE:
- Open tickets: {open_count}
- Active SLA breaches: {breach_count}
- Critical tickets open: {critical_count}
- High priority tickets open: {high_count}
- Overall SLA: {kpis['sla_met_percent']}%
- Resolution rate: {kpis['resolution_rate']}%

TEAM SLA BREAKDOWN:
{chr(10).join([f"- {t['team_name']}: {t['sla_percent']}% SLA, {t['open']} open, {t['active_breaches']} breaches" for t in sla['team_breakdown']])}

DETECTED SIGNALS:
{chr(10).join(anomalies_found) if anomalies_found else 'No critical anomalies detected'}

Provide an Anomaly Detection Report:
1. **Anomaly Status** (🟢 Normal / 🟡 Warning / 🔴 Critical)
2. **Detected Anomalies** (list each with severity and impact)
3. **Pattern Analysis** (what these patterns suggest)
4. **Immediate Actions Required** (within next 2 hours)
5. **Monitoring Recommendations** (what to watch closely)

Be specific about which teams/categories are affected."""

    result = await rag_chat(prompt, [], live_context={"kpis": kpis})

    # Determine overall severity
    if breach_count > 10 or critical_count > 3 or teams_below_80:
        severity = "critical"
        severity_color = "#A32D2D"
    elif breach_count > 5 or high_count > 15:
        severity = "warning"
        severity_color = "#BA7517"
    else:
        severity = "normal"
        severity_color = "#0F6E56"

    return {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "severity":       severity,
        "severity_color": severity_color,
        "anomalies_found": anomalies_found,
        "anomaly_count":  len(anomalies_found),
        "report":         result["reply"],
        "metrics": {
            "breach_count":    breach_count,
            "critical_open":   critical_count,
            "high_open":       high_count,
            "teams_at_risk":   [t["team_name"] for t in teams_below_80],
        }
    }
