"""
app/api/connector.py — Universal API Connector
Connects ServicePulse to any ticketing system via REST API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import httpx
import json
import logging

from app.db.database import get_db

logger = logging.getLogger(__name__)
connector_router = APIRouter(prefix="/api/connectors", tags=["Connectors"])

# ── In-memory connector store (persists via DB in production) ──
CONNECTORS: dict = {}


# ── Schemas ────────────────────────────────────────────────

class ConnectorConfig(BaseModel):
    name: str                          # e.g. "TicketFlow", "Jira", "Freshservice"
    base_url: str                      # e.g. "https://ticketflow-g671.onrender.com"
    api_key: Optional[str] = None      # API key if required
    auth_type: str = "none"            # "none", "bearer", "basic", "apikey"
    tickets_endpoint: str = "/api/tickets"
    summary_endpoint: str = "/api/summary"
    sync_endpoint: str = "/api/sync"
    field_mapping: Optional[dict] = None   # map their fields to ServicePulse fields
    auto_sync: bool = True
    sync_interval_seconds: int = 60

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    auto_sync: Optional[bool] = None
    sync_interval_seconds: Optional[int] = None

# ── Default field mappings per system ─────────────────────

DEFAULT_MAPPINGS = {
    "ticketflow": {
        "id":           "ticket_number",
        "subject":      "subject",
        "status":       "status",
        "priority":     "priority",
        "team":         "team_name",
        "assignee":     "agent_name",
        "created_at":   "created_at",
        "updated_at":   "updated_at",
        "category":     "category",
    },
    "jira": {
        "id":           "key",
        "subject":      "fields.summary",
        "status":       "fields.status.name",
        "priority":     "fields.priority.name",
        "team":         "fields.project.name",
        "assignee":     "fields.assignee.displayName",
        "created_at":   "fields.created",
        "updated_at":   "fields.updated",
        "category":     "fields.issuetype.name",
    },
    "freshservice": {
        "id":           "id",
        "subject":      "subject",
        "status":       "status",
        "priority":     "priority",
        "team":         "group_id",
        "assignee":     "responder_id",
        "created_at":   "created_at",
        "updated_at":   "updated_at",
        "category":     "category",
    },
    "zendesk": {
        "id":           "id",
        "subject":      "subject",
        "status":       "status",
        "priority":     "priority",
        "team":         "group_id",
        "assignee":     "assignee_id",
        "created_at":   "created_at",
        "updated_at":   "updated_at",
        "category":     "ticket_form_id",
    },
    "servicedesk_plus": {
        "id":           "id",
        "subject":      "subject",
        "status":       "status.name",
        "priority":     "priority.name",
        "team":         "group.name",
        "assignee":     "technician.name",
        "created_at":   "created_time",
        "updated_at":   "last_updated_time",
        "category":     "category.name",
    },
    "custom": {
        "id":           "id",
        "subject":      "subject",
        "status":       "status",
        "priority":     "priority",
        "team":         "team",
        "assignee":     "assignee",
        "created_at":   "created_at",
        "updated_at":   "updated_at",
        "category":     "category",
    }
}


# ── Helper — get nested value from dict ───────────────────

def get_nested(data: dict, path: str, default="—"):
    keys = path.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, default)
        else:
            return default
    return val if val is not None else default


# ── Build auth headers ─────────────────────────────────────

def build_headers(connector: dict) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    auth_type = connector.get("auth_type", "none")
    api_key   = connector.get("api_key", "")
    if auth_type == "bearer" and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif auth_type == "apikey" and api_key:
        headers["X-API-Key"] = api_key
        headers["apikey"]    = api_key
    return headers


# ── Normalize ticket from any system to ServicePulse format ──

def normalize_ticket(raw: dict, mapping: dict, source: str) -> dict:
    return {
        "id":           get_nested(raw, mapping.get("id", "id")),
        "subject":      get_nested(raw, mapping.get("subject", "subject")),
        "status":       get_nested(raw, mapping.get("status", "status")),
        "priority":     get_nested(raw, mapping.get("priority", "priority")),
        "team_name":    get_nested(raw, mapping.get("team", "team_name")),
        "assignee_name":get_nested(raw, mapping.get("assignee", "assignee")),
        "created_at":   get_nested(raw, mapping.get("created_at", "created_at")),
        "updated_at":   get_nested(raw, mapping.get("updated_at", "updated_at")),
        "category":     get_nested(raw, mapping.get("category", "category")),
        "source":       source,
        "raw":          raw,
    }


# ── CRUD Endpoints ─────────────────────────────────────────

@connector_router.get("")
def list_connectors():
    """List all configured connectors."""
    return list(CONNECTORS.values())


@connector_router.post("", status_code=201)
def add_connector(config: ConnectorConfig):
    """Add a new ticketing system connector."""
    connector_id = config.name.lower().replace(" ", "_")
    system_type  = connector_id.split("_")[0]
    mapping = config.field_mapping or DEFAULT_MAPPINGS.get(system_type, DEFAULT_MAPPINGS["custom"])

    CONNECTORS[connector_id] = {
        "id":            connector_id,
        "name":          config.name,
        "base_url":      config.base_url.rstrip("/"),
        "api_key":       config.api_key,
        "auth_type":     config.auth_type,
        "tickets_endpoint": config.tickets_endpoint,
        "summary_endpoint": config.summary_endpoint,
        "sync_endpoint":    config.sync_endpoint,
        "field_mapping": mapping,
        "auto_sync":     config.auto_sync,
        "sync_interval": config.sync_interval_seconds,
        "status":        "pending",
        "last_sync":     None,
        "last_error":    None,
        "ticket_count":  0,
        "added_at":      datetime.now(timezone.utc).isoformat(),
    }
    return CONNECTORS[connector_id]


@connector_router.delete("/{connector_id}", status_code=204)
def remove_connector(connector_id: str):
    if connector_id not in CONNECTORS:
        raise HTTPException(404, "Connector not found")
    del CONNECTORS[connector_id]


# ── Test Connection ────────────────────────────────────────

@connector_router.post("/{connector_id}/test")
async def test_connector(connector_id: str):
    """Test connectivity to the ticketing system."""
    if connector_id not in CONNECTORS:
        raise HTTPException(404, "Connector not found")

    connector = CONNECTORS[connector_id]
    headers   = build_headers(connector)
    test_url  = connector["base_url"] + "/health"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(test_url, headers=headers)
            CONNECTORS[connector_id]["status"] = "connected" if res.status_code < 400 else "error"
            return {
                "status": "connected" if res.status_code < 400 else "error",
                "status_code": res.status_code,
                "response": res.json() if res.headers.get("content-type","").startswith("application/json") else res.text[:200]
            }
    except Exception as e:
        CONNECTORS[connector_id]["status"] = "error"
        CONNECTORS[connector_id]["last_error"] = str(e)
        return {"status": "error", "message": str(e)}


# ── Sync Tickets ───────────────────────────────────────────

@connector_router.post("/{connector_id}/sync")
async def sync_connector(connector_id: str):
    """Pull latest tickets from the connected ticketing system."""
    if connector_id not in CONNECTORS:
        raise HTTPException(404, "Connector not found")

    connector = CONNECTORS[connector_id]
    headers   = build_headers(connector)
    mapping   = connector["field_mapping"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:

            # Try /api/summary first (TicketFlow-compatible)
            summary_url = connector["base_url"] + connector["summary_endpoint"]
            tickets_url = connector["base_url"] + connector["tickets_endpoint"]

            summary_data = None
            try:
                res = await client.get(summary_url, headers=headers)
                if res.status_code == 200:
                    summary_data = res.json()
            except:
                pass

            # Get tickets
            res = await client.get(tickets_url, headers=headers)
            raw_data = res.json()

            # Handle different response formats
            if isinstance(raw_data, list):
                raw_tickets = raw_data
            elif isinstance(raw_data, dict):
                raw_tickets = raw_data.get("tickets") or raw_data.get("issues") or raw_data.get("results") or raw_data.get("data") or []
            else:
                raw_tickets = []

            # Normalize
            normalized = [normalize_ticket(t, mapping, connector["name"]) for t in raw_tickets]

            # Update connector status
            CONNECTORS[connector_id].update({
                "status":       "connected",
                "last_sync":    datetime.now(timezone.utc).isoformat(),
                "ticket_count": len(normalized),
                "last_error":   None,
                "cached_tickets": normalized,
                "cached_summary": summary_data,
            })

            return {
                "status":     "success",
                "source":     connector["name"],
                "synced_at":  CONNECTORS[connector_id]["last_sync"],
                "count":      len(normalized),
                "tickets":    normalized[:20],   # return first 20
                "summary":    summary_data,
            }

    except Exception as e:
        CONNECTORS[connector_id]["status"]     = "error"
        CONNECTORS[connector_id]["last_error"] = str(e)
        raise HTTPException(500, f"Sync failed: {str(e)}")


# ── Get Synced Data ────────────────────────────────────────

@connector_router.get("/{connector_id}/tickets")
def get_connector_tickets(connector_id: str):
    """Get the last synced tickets from a connector."""
    if connector_id not in CONNECTORS:
        raise HTTPException(404, "Connector not found")
    connector = CONNECTORS[connector_id]
    return {
        "source":    connector["name"],
        "last_sync": connector.get("last_sync"),
        "count":     connector.get("ticket_count", 0),
        "tickets":   connector.get("cached_tickets", []),
    }


@connector_router.get("/{connector_id}/summary")
def get_connector_summary(connector_id: str):
    """Get the last synced summary from a connector."""
    if connector_id not in CONNECTORS:
        raise HTTPException(404, "Connector not found")
    connector = CONNECTORS[connector_id]
    return connector.get("cached_summary") or {"message": "No data synced yet. Run sync first."}


# ── All Sources Combined ───────────────────────────────────

@connector_router.get("/all/tickets")
def get_all_tickets():
    """Combined tickets from all connected systems."""
    all_tickets = []
    for conn in CONNECTORS.values():
        all_tickets.extend(conn.get("cached_tickets", []))
    return {
        "total":   len(all_tickets),
        "sources": [c["name"] for c in CONNECTORS.values() if c.get("status") == "connected"],
        "tickets": all_tickets
    }
