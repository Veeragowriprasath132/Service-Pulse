"""
app/models/ — SQLAlchemy ORM models
All models in one file for simplicity; split into separate files in larger apps.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base


# ── Enums ─────────────────────────────────────────────────

class PriorityEnum(str, enum.Enum):
    low      = "Low"
    medium   = "Medium"
    high     = "High"
    critical = "Critical"

class StatusEnum(str, enum.Enum):
    open       = "Open"
    in_progress= "In Progress"
    resolved   = "Resolved"
    closed     = "Closed"
    sla_breach = "SLA Breach"

class WorkloadEnum(str, enum.Enum):
    normal   = "normal"
    moderate = "moderate"
    high     = "high"


# ── Team ──────────────────────────────────────────────────

class Team(Base):
    __tablename__ = "teams"

    id          = Column(Integer, primary_key=True, index=True)
    slug        = Column(String(50), unique=True, nullable=False)
    name        = Column(String(100), nullable=False)
    description = Column(String(255))
    domain      = Column(String(100))          # category keyword this team handles
    lead_name   = Column(String(100))
    color       = Column(String(20), default="#E6F1FB")
    text_color  = Column(String(20), default="#0C447C")
    badge_color = Column(String(20), default="#185FA5")
    sla_target  = Column(Float, default=95.0)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    members = relationship("Member", back_populates="team", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="team")


# ── Member ────────────────────────────────────────────────

class Member(Base):
    __tablename__ = "members"

    id         = Column(Integer, primary_key=True, index=True)
    team_id    = Column(Integer, ForeignKey("teams.id"), nullable=False)
    name       = Column(String(100), nullable=False)
    role       = Column(String(100))
    email      = Column(String(150), unique=True)
    initials   = Column(String(4))
    workload   = Column(Enum(WorkloadEnum), default=WorkloadEnum.normal)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    team    = relationship("Team", back_populates="members")
    tickets = relationship("Ticket", back_populates="assignee")


# ── SLA Rule ──────────────────────────────────────────────

class SLARule(Base):
    __tablename__ = "sla_rules"

    id                  = Column(Integer, primary_key=True, index=True)
    priority            = Column(Enum(PriorityEnum), nullable=False)
    response_hours      = Column(Float, nullable=False)   # first response SLA
    resolution_hours    = Column(Float, nullable=False)   # full resolution SLA
    description         = Column(String(255))

    tickets = relationship("Ticket", back_populates="sla_rule")


# ── Ticket ────────────────────────────────────────────────

class Ticket(Base):
    __tablename__ = "tickets"

    id            = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(20), unique=True, nullable=False)  # "TK-1001"
    subject       = Column(String(300), nullable=False)
    description   = Column(Text)
    category      = Column(String(100))
    priority      = Column(Enum(PriorityEnum), default=PriorityEnum.medium)
    status        = Column(Enum(StatusEnum), default=StatusEnum.open)
    ticket_type   = Column(String(50), default="Incident")

    # Relationships
    team_id       = Column(Integer, ForeignKey("teams.id"))
    assignee_id   = Column(Integer, ForeignKey("members.id"), nullable=True)
    sla_rule_id   = Column(Integer, ForeignKey("sla_rules.id"), nullable=True)

    # Reporter
    reporter_name  = Column(String(100))
    reporter_email = Column(String(150))
    reporter_phone = Column(String(50))

    # Timestamps
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    resolved_at   = Column(DateTime, nullable=True)

    # SLA tracking
    sla_due_at        = Column(DateTime, nullable=True)
    sla_met           = Column(Boolean, nullable=True)
    sla_breach_at     = Column(DateTime, nullable=True)
    sla_breach_minutes= Column(Float, nullable=True)   # minutes overdue if breached

    # AI fields
    ai_routing_confidence = Column(Float, nullable=True)   # 0-1
    ai_routing_reason     = Column(Text, nullable=True)
    ai_predicted_sla_risk = Column(Float, nullable=True)   # 0-1 probability of breach
    embedding_text        = Column(Text, nullable=True)    # text used for RAG embedding

    # Extra metadata
    tags          = Column(JSON, default=list)
    resolution_note = Column(Text)

    team     = relationship("Team", back_populates="tickets")
    assignee = relationship("Member", back_populates="tickets")
    sla_rule = relationship("SLARule", back_populates="tickets")


# ── KnowledgeBase (RAG source documents) ──────────────────

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String(300), nullable=False)
    content    = Column(Text, nullable=False)
    category   = Column(String(100))
    tags       = Column(JSON, default=list)
    embedding  = Column(JSON, nullable=True)    # stored as list of floats
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
