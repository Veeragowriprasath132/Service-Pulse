"""
app/db/init_db.py — Create tables and seed initial data
"""
from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.models.models import Team, Member, Ticket, SLARule, StatusEnum, PriorityEnum, WorkloadEnum

logger = logging.getLogger(__name__)


def seed_if_empty():
    db = SessionLocal()
    try:
        if db.query(Team).count() > 0:
            logger.info("Database already has data — skipping seed.")
            return
        logger.info("Seeding database with initial data...")
        seed_all(db)
        logger.info("Seeding complete.")
    finally:
        db.close()


def seed_all(db: Session):
    # SLA Rules
    for pri, rh, rsh in [
        (PriorityEnum.critical, 1, 4),
        (PriorityEnum.high, 2, 8),
        (PriorityEnum.medium, 4, 24),
        (PriorityEnum.low, 8, 72),
    ]:
        db.add(SLARule(priority=pri, response_hours=rh, resolution_hours=rsh))
    db.flush()

    # Teams
    teams_data = [
        ("network",  "Network Ops",      "LAN/WAN, VPN, Firewall",              "Network",        "Ravi Kumar",    "#E6F1FB","#0C447C","#185FA5", 97.0),
        ("security", "Security",          "Cybersecurity, IAM, Compliance",       "Security",       "Priya Singh",   "#FCEBEB","#791F1F","#A32D2D", 94.0),
        ("hardware", "Hardware",           "Endpoints, Printers, Assets",          "Hardware",       "Deepa Nair",    "#FAEEDA","#633806","#BA7517", 91.0),
        ("software", "Software",           "Applications, Licenses, OS",           "Software",       "Karthik V",     "#EAF3DE","#27500A","#3B6D11", 89.0),
        ("infra",    "Infra & Servers",    "Servers, VMware, Cloud",               "Infrastructure", "Suresh Babu",   "#EEEDFE","#3C3489","#534AB7", 95.0),
        ("bi",       "BI & Analytics",     "Power BI, Dashboards, Reporting",      "BI & Analytics", "Anand Raj",     "#E1F5EE","#085041","#0F6E56", 93.0),
        ("db",       "DB & Middleware",    "SQL, APIs, Middleware",                "Database",       "Meena Pillai",  "#FAECE7","#712B13","#993C1D", 88.0),
    ]
    teams = {}
    for slug, name, desc, domain, lead, color, tc, bc, sla in teams_data:
        t = Team(slug=slug, name=name, description=desc, domain=domain,
                 lead_name=lead, color=color, text_color=tc, badge_color=bc, sla_target=sla)
        db.add(t)
        db.flush()
        teams[slug] = t

    # Members
    members_raw = {
        "network":  [("Ravi Kumar","Lead Engineer","ravi.kumar@atlas.in","RK","normal"),("Arun Selvan","Network Engineer","arun.selvan@atlas.in","AS","normal"),("Bharathi M","L2 Support","bharathi.m@atlas.in","BM","normal"),("Chandru P","L1 Support","chandru.p@atlas.in","CP","moderate"),("Divya R","Network Engineer","divya.r@atlas.in","DR","normal"),("Elango K","L2 Support","elango.k@atlas.in","EK","high")],
        "security": [("Priya Singh","Security Lead","priya.singh@atlas.in","PS","normal"),("Ganesh V","Security Analyst","ganesh.v@atlas.in","GV","moderate"),("Harini L","IAM Specialist","harini.l@atlas.in","HL","normal"),("Ilango S","Threat Analyst","ilango.s@atlas.in","IS","normal"),("Jayashree P","Compliance Analyst","jayashree.p@atlas.in","JP","normal")],
        "hardware": [("Deepa Nair","Hardware Lead","deepa.nair@atlas.in","DN","normal"),("Karthi M","Field Technician","karthi.m@atlas.in","KM","moderate"),("Lalitha R","Asset Manager","lalitha.r@atlas.in","LR","normal"),("Mani K","L1 Support","mani.k@atlas.in","MK","high"),("Nithya B","Field Technician","nithya.b@atlas.in","NB","normal"),("Oviya S","Procurement Lead","oviya.s@atlas.in","OS","normal"),("Prasad T","L2 Support","prasad.t@atlas.in","PT","normal")],
        "software": [("Karthik V","Software Lead","karthik.v@atlas.in","KV","normal"),("Ramya D","App Support","ramya.d@atlas.in","RD","moderate"),("Senthil G","L2 Support","senthil.g@atlas.in","SG","normal"),("Thenmozhi K","License Admin","thenmozhi.k@atlas.in","TK","normal"),("Uma P","App Support","uma.p@atlas.in","UP","normal"),("Vasanth R","L1 Support","vasanth.r@atlas.in","VR","normal")],
        "infra":    [("Suresh Babu","Infra Lead","suresh.babu@atlas.in","SB","high"),("Aarthi N","Server Admin","aarthi.n@atlas.in","AN","moderate"),("Balamurugan S","Cloud Ops","bala.s@atlas.in","BS","normal"),("Chithra M","VMware Specialist","chithra.m@atlas.in","CM","normal"),("Dhanasekar V","L2 Support","dhanasekar.v@atlas.in","DV","moderate")],
        "bi":       [("Anand Raj","BI Lead","anand.raj@atlas.in","AR","normal"),("Eswari K","Data Analyst","eswari.k@atlas.in","EK","normal"),("Fathima Z","Report Developer","fathima.z@atlas.in","FZ","normal"),("Gopinath S","Tableau Developer","gopinath.s@atlas.in","GS","moderate")],
        "db":       [("Meena Pillai","DB Lead","meena.pillai@atlas.in","MP","moderate"),("Naveen C","Database Admin","naveen.c@atlas.in","NC","normal"),("Pavithra S","Middleware Engineer","pavithra.s@atlas.in","PS","normal"),("Rajkumar D","API Developer","rajkumar.d@atlas.in","RD","normal"),("Saranya V","L2 Support","saranya.v@atlas.in","SV","normal")],
    }
    members = {}
    for slug, mlist in members_raw.items():
        for name, role, email, initials, wl in mlist:
            m = Member(team_id=teams[slug].id, name=name, role=role, email=email,
                       initials=initials, workload=WorkloadEnum(wl))
            db.add(m)
            db.flush()
            members[email] = m

    # Tickets
    now = datetime.now(timezone.utc)
    sla_h = {"Critical":4,"High":8,"Medium":24,"Low":72}
    pm = {"Critical":PriorityEnum.critical,"High":PriorityEnum.high,"Medium":PriorityEnum.medium,"Low":PriorityEnum.low}
    sm = {"Open":StatusEnum.open,"In Progress":StatusEnum.in_progress,"Resolved":StatusEnum.resolved,"SLA Breach":StatusEnum.sla_breach}

    tickets_data = [
        ("VPN connectivity failure in Block-C","Network","High","In Progress","network","ravi.kumar@atlas.in",0,False,None),
        ("Email server TLS certificate expiry","Security","High","Open","security","priya.singh@atlas.in",0,False,None),
        ("Power BI dashboard not loading","BI & Analytics","Medium","In Progress","bi","anand.raj@atlas.in",0,False,None),
        ("Laptop battery replacement","Hardware","Low","Resolved","hardware","deepa.nair@atlas.in",1,True,True),
        ("AD group policy not applying","Infrastructure","Medium","SLA Breach","infra","suresh.babu@atlas.in",1,False,False),
        ("SQL query timeout in production","Database","High","In Progress","db","meena.pillai@atlas.in",1,False,None),
        ("Antivirus definitions outdated","Security","Medium","Resolved","security","ganesh.v@atlas.in",1,True,True),
        ("Office 365 activation failure","Software","Medium","Open","software","karthik.v@atlas.in",2,False,None),
        ("Cisco switch port down floor 2","Network","High","Resolved","network","arun.selvan@atlas.in",2,True,True),
        ("Projector not detected in conf room","Hardware","Low","Resolved","hardware","karthi.m@atlas.in",2,True,True),
        ("DB replication lag exceeding threshold","Database","High","SLA Breach","db","naveen.c@atlas.in",2,False,False),
        ("Firewall rule blocking internal APIs","Network","High","Open","network","bharathi.m@atlas.in",2,False,None),
        ("User account lockout in HR dept","Security","Medium","Resolved","security","harini.l@atlas.in",3,True,True),
        ("VMware ESXi host health warnings","Infrastructure","Medium","In Progress","infra","chithra.m@atlas.in",3,False,None),
        ("Tableau license expiry alert","BI & Analytics","Medium","Open","bi","gopinath.s@atlas.in",3,False,None),
        ("Printer queue stuck floor 3","Hardware","Low","SLA Breach","hardware","mani.k@atlas.in",4,False,False),
        ("Cloud storage sync failure","Infrastructure","Medium","In Progress","infra","bala.s@atlas.in",4,False,None),
        ("REST API returning 500 errors","Database","High","Open","db","pavithra.s@atlas.in",4,False,None),
        ("Windows 11 upgrade rollout issues","Software","Medium","Resolved","software","ramya.d@atlas.in",5,True,True),
        ("Network bandwidth spike investigation","Network","Medium","Resolved","network","divya.r@atlas.in",5,True,True),
    ]

    for i, (subject, category, priority, status, team_slug, email, days_ago, resolved, sla_met) in enumerate(tickets_data):
        created = now - timedelta(days=days_ago, hours=i*2)
        sla_due = created + timedelta(hours=sla_h[priority])
        resolved_at = (created + timedelta(hours=sla_h[priority]*0.8)) if resolved else None
        t = Ticket(
            ticket_number=f"TK-{1229+i}",
            subject=subject, category=category,
            priority=pm[priority], status=sm[status],
            team_id=teams[team_slug].id,
            assignee_id=members.get(email) and members[email].id,
            created_at=created, updated_at=created,
            sla_due_at=sla_due, resolved_at=resolved_at, sla_met=sla_met,
            embedding_text=f"{subject} {category}", reporter_name="System",
        )
        if status == "SLA Breach":
            t.sla_breach_at = now
            t.sla_breach_minutes = max((now - sla_due).total_seconds()/60, 10)
        db.add(t)

    db.commit()
    logger.info("Seeded %d teams, %d members, %d tickets", len(teams), len(members), len(tickets_data))
