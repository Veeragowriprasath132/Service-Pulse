# ServiceDesk HQ — Full Stack Application
### Project ATLAS · v2.0

> Leadership dashboard + AI-powered ticketing system built with FastAPI, Python, SQLAlchemy, PostgreSQL, RAG, and ML.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | **FastAPI** | REST API framework |
| Backend | **Python 3.11+** | Core language |
| Backend | **SQLAlchemy 2.0** | ORM & database abstraction |
| Database | **PostgreSQL / MySQL** | Production data store |
| AI/ML | **RAG Pipeline** | Context-aware AI responses |
| AI/ML | **scikit-learn / ML** | Ticket routing & SLA prediction |
| AI Agents | **Intelligent Routing** | Auto-assign tickets to teams |
| AI Agents | **SLA Compliance** | Real-time breach prediction |
| Frontend | **HTML / CSS / JS** | Dashboard UI |
| Tools | **VS Code, GitHub Copilot, Claude** | Development environment |

---

## Project Structure

```
servicedesk-pro/
├── backend/
│   ├── app/
│   │   ├── main.py                 ← FastAPI app entry point
│   │   ├── config.py               ← Settings & env vars
│   │   ├── db/
│   │   │   ├── database.py         ← SQLAlchemy engine & session
│   │   │   └── init_db.py          ← DB init & seed data
│   │   ├── models/
│   │   │   ├── ticket.py           ← Ticket ORM model
│   │   │   ├── team.py             ← Team ORM model
│   │   │   ├── member.py           ← Member ORM model
│   │   │   └── sla.py              ← SLA rule ORM model
│   │   ├── schemas/
│   │   │   ├── ticket.py           ← Pydantic request/response schemas
│   │   │   ├── team.py             ← Team schemas
│   │   │   └── dashboard.py        ← Dashboard summary schemas
│   │   ├── api/
│   │   │   ├── tickets.py          ← Ticket CRUD endpoints
│   │   │   ├── teams.py            ← Team & member endpoints
│   │   │   ├── dashboard.py        ← KPI & summary endpoints
│   │   │   ├── sla.py              ← SLA tracking endpoints
│   │   │   └── ai.py               ← AI assistant & routing endpoints
│   │   ├── services/
│   │   │   ├── ticket_service.py   ← Business logic for tickets
│   │   │   ├── sla_service.py      ← SLA calculation & monitoring
│   │   │   └── dashboard_service.py← KPI aggregation logic
│   │   ├── ai/
│   │   │   ├── rag_pipeline.py     ← RAG: embed + retrieve + generate
│   │   │   ├── routing_agent.py    ← ML-based ticket routing agent
│   │   │   ├── sla_predictor.py    ← ML model for SLA breach prediction
│   │   │   └── vector_store.py     ← In-memory vector store (FAISS/numpy)
│   │   └── utils/
│   │       ├── logger.py           ← Structured logging
│   │       └── helpers.py          ← Utility functions
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py                      ← Start server
├── frontend/
│   ├── index.html                  ← Main dashboard
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js                  ← API client (calls FastAPI)
│       ├── app.js                  ← Main app logic
│       └── charts.js               ← Chart rendering
├── scripts/
│   ├── setup_db.py                 ← DB setup script
│   └── seed_data.py                ← Insert sample data
├── docker-compose.yml              ← One-command full stack
├── Dockerfile.backend
└── README.md
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+ (or MySQL 8+)
- Node.js (optional, for live reload)

### 1. Clone & setup environment

```bash
cd servicedesk-pro/backend
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your DB credentials and API keys
```

### 3. Setup database

```bash
# Make sure PostgreSQL is running, then:
python scripts/setup_db.py      # Creates tables
python scripts/seed_data.py     # Inserts sample data
```

### 4. Start the backend

```bash
python run.py
# API running at: http://localhost:8000
# Docs at:        http://localhost:8000/docs
# ReDoc at:       http://localhost:8000/redoc
```

### 5. Open the frontend

```bash
# Option A: Simple
open frontend/index.html

# Option B: Python server (no CORS issues)
cd frontend && python3 -m http.server 3000
# Open http://localhost:3000
```

---

## Docker (One-command setup)

```bash
# Start everything (Postgres + Backend + Frontend)
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

---

## API Endpoints

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/summary` | All KPIs |
| GET | `/api/dashboard/sla` | SLA metrics |
| GET | `/api/dashboard/workload` | Team workload |
| GET | `/api/dashboard/trends` | Ticket volume trend |

### Tickets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tickets` | List with filters |
| POST | `/api/tickets` | Create & auto-assign |
| GET | `/api/tickets/{id}` | Get single ticket |
| PATCH | `/api/tickets/{id}` | Update ticket |
| DELETE | `/api/tickets/{id}` | Delete ticket |

### Teams
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/teams` | All teams |
| GET | `/api/teams/{id}/members` | Team members |
| GET | `/api/teams/{id}/tickets` | Team tickets |

### AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/chat` | AI assistant (RAG) |
| POST | `/api/ai/route` | Auto-route ticket |
| POST | `/api/ai/predict-sla` | SLA breach prediction |
| GET | `/api/ai/insights` | Auto-generated insights |

---

## Environment Variables (.env)

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/servicedesk
# or MySQL: mysql+pymysql://user:password@localhost:3306/servicedesk

# Anthropic (for AI assistant)
ANTHROPIC_API_KEY=sk-ant-...

# App
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
