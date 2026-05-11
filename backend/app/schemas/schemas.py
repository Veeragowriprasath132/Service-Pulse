"""
app/schemas/schemas.py — Pydantic v2 request / response schemas
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, field_validator
from app.models.models import PriorityEnum, StatusEnum, WorkloadEnum


# ════════════════════════════════════════════════════════
#  TEAM SCHEMAS
# ════════════════════════════════════════════════════════

class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None
    lead_name: Optional[str] = None
    sla_target: float = 95.0

class TeamCreate(TeamBase):
    slug: str

class TeamOut(TeamBase):
    id: int
    slug: str
    color: str
    badge_color: str
    member_count: int = 0
    open_tickets: int = 0
    resolved_tickets: int = 0
    sla_percent: float = 0.0
    model_config = {"from_attributes": True}

class TeamDetail(TeamOut):
    members: List["MemberOut"] = []


# ════════════════════════════════════════════════════════
#  MEMBER SCHEMAS
# ════════════════════════════════════════════════════════

class MemberBase(BaseModel):
    name: str
    role: Optional[str] = None
    email: Optional[str] = None

class MemberCreate(MemberBase):
    team_id: int
    initials: Optional[str] = None

class MemberOut(MemberBase):
    id: int
    team_id: int
    initials: Optional[str]
    workload: WorkloadEnum
    open_tickets: int = 0
    resolved_tickets: int = 0
    sla_percent: float = 0.0
    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════
#  TICKET SCHEMAS
# ════════════════════════════════════════════════════════

class TicketCreate(BaseModel):
    subject: str
    description: Optional[str] = None
    category: str
    priority: PriorityEnum = PriorityEnum.medium
    ticket_type: str = "Incident"
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_phone: Optional[str] = None
    tags: List[str] = []

    @field_validator("subject")
    @classmethod
    def subject_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()

class TicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StatusEnum] = None
    priority: Optional[PriorityEnum] = None
    assignee_id: Optional[int] = None
    resolution_note: Optional[str] = None
    tags: Optional[List[str]] = None

class TicketOut(BaseModel):
    id: int
    ticket_number: str
    subject: str
    description: Optional[str]
    category: Optional[str]
    priority: PriorityEnum
    status: StatusEnum
    ticket_type: str
    team_name: Optional[str] = None
    assignee_name: Optional[str] = None
    reporter_name: Optional[str]
    reporter_email: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    sla_due_at: Optional[datetime]
    sla_met: Optional[bool]
    sla_breach_minutes: Optional[float]
    ai_routing_confidence: Optional[float]
    ai_predicted_sla_risk: Optional[float]
    tags: List[Any] = []
    model_config = {"from_attributes": True}

class TicketListParams(BaseModel):
    status: Optional[StatusEnum] = None
    team_id: Optional[int] = None
    priority: Optional[PriorityEnum] = None
    category: Optional[str] = None
    assignee_id: Optional[int] = None
    search: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sort_by: str = "created_at"
    sort_dir: str = "desc"
    page: int = 1
    page_size: int = 50


# ════════════════════════════════════════════════════════
#  DASHBOARD SCHEMAS
# ════════════════════════════════════════════════════════

class KPISummary(BaseModel):
    total_tickets: int
    resolved: int
    resolution_rate: float
    open_tickets: int
    in_progress: int
    sla_met_percent: float
    active_breaches: int
    avg_resolution_hours: float
    csat_score: float
    active_engineers: int

class TeamSLASummary(BaseModel):
    team_id: int
    team_name: str
    sla_percent: float
    open: int
    resolved: int
    active_breaches: int
    avg_resolution_hours: float

class SLADashboard(BaseModel):
    overall_sla: float
    target: float
    active_breaches: int
    avg_resolution_hours: float
    team_breakdown: List[TeamSLASummary]
    monthly_trend: List[dict]

class WorkloadSummary(BaseModel):
    team_id: int
    team_name: str
    open_tickets: int
    member_count: int
    avg_per_member: float
    overloaded_count: int

class DashboardResponse(BaseModel):
    kpis: KPISummary
    sla: SLADashboard
    workload: List[WorkloadSummary]
    recent_tickets: List[TicketOut]


# ════════════════════════════════════════════════════════
#  AI SCHEMAS
# ════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str
    content: str

class AIChat(BaseModel):
    message: str
    history: List[ChatMessage] = []

class AIResponse(BaseModel):
    reply: str
    sources: List[str] = []
    confidence: float = 1.0

class RouteRequest(BaseModel):
    subject: str
    description: Optional[str] = None
    category: Optional[str] = None

class RouteResponse(BaseModel):
    recommended_team_id: int
    recommended_team_name: str
    confidence: float
    reasoning: str
    alternative_teams: List[dict] = []

class SLAPredictRequest(BaseModel):
    ticket_id: Optional[int] = None
    subject: str
    priority: PriorityEnum
    category: str
    team_name: Optional[str] = None
    reporter_email: Optional[str] = None

class SLAPredictResponse(BaseModel):
    breach_probability: float
    risk_level: str          # "low" | "medium" | "high" | "critical"
    predicted_resolution_hours: float
    recommendation: str

class InsightItem(BaseModel):
    title: str
    body: str
    severity: str   # "info" | "warning" | "critical"
    team: Optional[str] = None
