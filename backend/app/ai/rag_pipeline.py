"""
app/ai/rag_pipeline.py
Retrieval-Augmented Generation pipeline:
  1. Embed query with sentence-transformers
  2. Retrieve top-K relevant knowledge chunks via cosine similarity
  3. Build context-enriched prompt
  4. Call Claude API with live project data + retrieved context
"""
from __future__ import annotations

import os
import json
import logging
import numpy as np
from typing import List, Tuple, Optional
from functools import lru_cache

import anthropic
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Knowledge base — seeded at startup ───────────────────
KNOWLEDGE_BASE: List[dict] = [
    {
        "id": "kb-001",
        "title": "SLA Policy — Priority Matrix",
        "content": (
            "Critical tickets must be responded to within 1 hour and resolved within 4 hours. "
            "High priority tickets: 2 hour response, 8 hour resolution. "
            "Medium priority: 4 hour response, 24 hour resolution. "
            "Low priority: 8 hour response, 72 hour resolution. "
            "SLA breaches are escalated automatically to the team lead after 50% of SLA time is consumed."
        ),
        "category": "SLA",
        "tags": ["sla", "priority", "response time", "resolution time"]
    },
    {
        "id": "kb-002",
        "title": "Network Ops Team — Scope & Responsibilities",
        "content": (
            "Network Ops handles: LAN/WAN issues, VPN connectivity, firewall rules, switch and router configuration, "
            "DNS/DHCP problems, bandwidth monitoring, network security incidents, Wi-Fi access point issues. "
            "Lead: Ravi Kumar. 6 engineers. Average SLA: 97%. "
            "Typical ticket keywords: VPN, firewall, network, switch, port, router, IP, DNS, Wi-Fi, connectivity."
        ),
        "category": "Teams",
        "tags": ["network", "vpn", "firewall", "routing"]
    },
    {
        "id": "kb-003",
        "title": "Security Team — Scope & Responsibilities",
        "content": (
            "Security team handles: certificate management (SSL/TLS), Identity and Access Management (IAM), "
            "antivirus and endpoint security, compliance audits, threat investigation, account lockouts, "
            "data breach response, SIEM alerts, firewall policy reviews. "
            "Lead: Priya Singh. 5 engineers. Average SLA: 94%. "
            "Keywords: certificate, SSL, TLS, IAM, AD, Active Directory, antivirus, lockout, compliance, threat."
        ),
        "category": "Teams",
        "tags": ["security", "certificates", "iam", "compliance"]
    },
    {
        "id": "kb-004",
        "title": "Hardware Team — Scope & Responsibilities",
        "content": (
            "Hardware team handles: laptop and desktop repairs, printer issues, projectors, monitors, peripherals, "
            "asset management, hardware procurement, battery replacements, physical server issues. "
            "Lead: Deepa Nair. 7 engineers. Average SLA: 91%. "
            "Keywords: laptop, desktop, printer, monitor, keyboard, mouse, projector, hardware, battery, cable."
        ),
        "category": "Teams",
        "tags": ["hardware", "laptop", "printer", "assets"]
    },
    {
        "id": "kb-005",
        "title": "Software Team — Scope & Responsibilities",
        "content": (
            "Software team handles: application installation and licensing, Office 365 issues, OS upgrades, "
            "software activation errors, patch management, browser issues, ERP/CRM application support. "
            "Lead: Karthik V. 6 engineers. Average SLA: 89%. "
            "Keywords: software, application, Office 365, license, activation, install, OS, Windows, patch."
        ),
        "category": "Teams",
        "tags": ["software", "office365", "licensing", "os"]
    },
    {
        "id": "kb-006",
        "title": "Infra & Servers Team — Scope & Responsibilities",
        "content": (
            "Infra & Servers handles: physical and virtual server management (VMware/ESXi), cloud infrastructure (Azure/AWS), "
            "Active Directory group policies, storage management, backup and recovery, CI/CD pipeline infrastructure, "
            "OneDrive/SharePoint sync issues. "
            "Lead: Suresh Babu. 5 engineers. Current SLA: 78% (below target — under review). "
            "Keywords: server, VMware, ESXi, Active Directory, AD, group policy, Azure, AWS, cloud, backup."
        ),
        "category": "Teams",
        "tags": ["infrastructure", "servers", "vmware", "active directory", "cloud"]
    },
    {
        "id": "kb-007",
        "title": "BI & Analytics Team — Scope & Responsibilities",
        "content": (
            "BI & Analytics team handles: Power BI dashboards, Tableau reports, data pipeline issues, "
            "SSRS reports, data gateway configuration, Excel data connections, analytics platform access. "
            "Lead: Anand Raj. 4 engineers. Average SLA: 93%. "
            "Keywords: Power BI, Tableau, dashboard, report, analytics, data, BI, SSRS, gateway."
        ),
        "category": "Teams",
        "tags": ["bi", "analytics", "powerbi", "tableau", "data"]
    },
    {
        "id": "kb-008",
        "title": "DB & Middleware Team — Scope & Responsibilities",
        "content": (
            "DB & Middleware team handles: SQL Server, MySQL, PostgreSQL database administration, "
            "query performance tuning, replication and clustering, REST API issues, middleware connectivity, "
            "connection pool management, stored procedures and indexing. "
            "Lead: Meena Pillai. 5 engineers. Average SLA: 88%. "
            "Keywords: database, SQL, MySQL, PostgreSQL, Oracle, API, middleware, query, replication, timeout."
        ),
        "category": "Teams",
        "tags": ["database", "sql", "middleware", "api"]
    },
    {
        "id": "kb-009",
        "title": "Escalation & Incident Management Process",
        "content": (
            "P1 Critical incidents: Immediate war room with all relevant team leads. "
            "P2 High: Escalate to team lead within 2 hours if unacknowledged. "
            "Cross-team tickets are handled by the primary team with collaboration requests to secondary teams. "
            "SLA breached tickets are escalated automatically and flagged in the leadership dashboard. "
            "Post-incident reviews are mandatory for P1 and P2 tickets."
        ),
        "category": "Process",
        "tags": ["escalation", "incident", "process", "p1", "p2"]
    },
    {
        "id": "kb-010",
        "title": "Project ATLAS — Overview and Objectives",
        "content": (
            "Project ATLAS is a large-scale enterprise IT transformation initiative. "
            "The project has 38 engineers across 7 specialized teams. "
            "Current status: 1248 total tickets, 87.2% resolution rate, 92.4% SLA compliance. "
            "Key challenge: Infra & Servers team at 78% SLA needs immediate attention. "
            "Target: 95% overall SLA compliance, CSAT > 4.5/5."
        ),
        "category": "Project",
        "tags": ["atlas", "project", "overview", "targets"]
    }
]

# ── Lazy-loaded embedding model ───────────────────────────
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformers model: %s", settings.embedding_model)
            _embedding_model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.warning("sentence-transformers not available: %s. Using TF-IDF fallback.", e)
    return _embedding_model


def embed_text(text: str) -> np.ndarray:
    """Return a numpy embedding vector for the given text."""
    model = get_embedding_model()
    if model is not None:
        return model.encode([text])[0]
    # Fallback: simple TF-IDF-like bag-of-words embedding (for environments without GPU)
    return _tfidf_embed(text)


def _tfidf_embed(text: str) -> np.ndarray:
    """Lightweight fallback embedding using character n-grams."""
    text = text.lower()
    size = 128
    vec = np.zeros(size)
    for i, char in enumerate(text):
        vec[ord(char) % size] += 1
    norm = np.linalg.norm(vec)
    return vec / (norm + 1e-9)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ── Pre-compute KB embeddings ─────────────────────────────
_kb_embeddings: Optional[List[Tuple[dict, np.ndarray]]] = None

def get_kb_embeddings() -> List[Tuple[dict, np.ndarray]]:
    global _kb_embeddings
    if _kb_embeddings is None:
        logger.info("Pre-computing knowledge base embeddings (%d documents)…", len(KNOWLEDGE_BASE))
        _kb_embeddings = [
            (doc, embed_text(doc["title"] + " " + doc["content"]))
            for doc in KNOWLEDGE_BASE
        ]
        logger.info("KB embeddings ready.")
    return _kb_embeddings


def retrieve_context(query: str, top_k: int = 5) -> List[dict]:
    """Retrieve the top_k most relevant knowledge documents for a query."""
    query_vec = embed_text(query)
    scored = [
        (doc, cosine_similarity(query_vec, vec))
        for doc, vec in get_kb_embeddings()
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, score in scored[:top_k] if score > 0.05]


# ── Main RAG function ─────────────────────────────────────

async def rag_chat(
    message: str,
    history: List[dict],
    live_context: Optional[dict] = None
) -> dict:
    """
    RAG-augmented chat:
    1. Retrieve relevant KB chunks
    2. Build enriched system prompt with KB + live data
    3. Call Claude API
    4. Return reply + source titles
    """
    # Step 1: Retrieve
    relevant_docs = retrieve_context(message, top_k=settings.max_context_chunks)
    kb_context = "\n\n".join(
        f"[{doc['title']}]\n{doc['content']}"
        for doc in relevant_docs
    )

    # Step 2: Build system prompt
    live_stats = ""
    if live_context:
        k = live_context.get("kpis", {})
        live_stats = f"""
LIVE PROJECT STATS (as of now):
- Total tickets: {k.get('total_tickets', 'N/A')}
- Resolved: {k.get('resolved', 'N/A')} ({k.get('resolution_rate', 'N/A')}% rate)
- Overall SLA: {k.get('sla_met_percent', 'N/A')}% (target 95%)
- Active SLA breaches: {k.get('active_breaches', 'N/A')}
- CSAT: {k.get('csat_score', 'N/A')}/5
- Active engineers: {k.get('active_engineers', 'N/A')} across 7 teams
"""

    system_prompt = f"""You are the AI assistant for ServiceDesk HQ — Project ATLAS.
You help leadership and managers understand ticket performance, team health, SLA compliance, and workload.
Be concise, data-driven, and actionable. Prioritise business impact in your recommendations.
{live_stats}
KNOWLEDGE BASE CONTEXT:
{kb_context}

Answer using the context and live stats above. If something is unknown, say so clearly."""

    # Step 3: Build messages
    messages = []
    for h in history[-10:]:   # limit history to last 10 turns
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    # Step 4: Call Claude
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text
    except Exception as e:
        logger.error("Claude API error: %s", e)
        reply = f"AI service temporarily unavailable. Error: {str(e)[:100]}"

    return {
        "reply": reply,
        "sources": [doc["title"] for doc in relevant_docs],
        "confidence": 0.95 if relevant_docs else 0.6
    }
