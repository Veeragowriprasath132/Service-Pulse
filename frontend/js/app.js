/* =========================================================
   ServiceDesk HQ — Main Application Logic
   ========================================================= */

// ── State ──────────────────────────────────────────────────
const State = {
  currentPage: 'dashboard',
  currentTeam: null,
  aiOpen: false,
  darkMode: localStorage.getItem('sdq-dark') === 'true',
  filters: { status:'', team:'', priority:'', category:'', search:'', dateFrom:'', dateTo:'', sort:'created', sortDir:'desc' },
  chartsInited: {},
  charts: {}
};

// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applyTheme();
  renderDashboard();
  renderAllTickets();
  renderTeamsPage();
  bindGlobalEvents();
  updateBadge();
});

function bindGlobalEvents() {
  document.getElementById('aiInput')?.addEventListener('keydown', e => { if (e.key === 'Enter') sendAI(); });
  document.getElementById('globalSearch')?.addEventListener('input', e => {
    const val = e.target.value.trim().toLowerCase();
    if (State.currentPage === 'tickets') {
      State.filters.search = val;
      renderAllTickets();
    }
  });
}

// ── Navigation ─────────────────────────────────────────────
function nav(page, el) {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');
  else {
    const found = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (found) found.classList.add('active');
  }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  State.currentPage = page;

const titles = {
    dashboard: ['Executive Dashboard', 'Real-time overview · Project ATLAS'],
    sla: ['SLA Monitor', 'Service Level Agreement tracking'],
    workload: ['Team Workload', 'Engineer capacity & distribution'],
    teams: ['Teams & Members', 'All teams in Project ATLAS'],
    tickets: ['All Tickets', 'Complete ticket registry'],
    create: ['Create Ticket', 'Raise & auto-assign new ticket'],
    connectors: ['Connectors', 'Connect any ticketing system to ServicePulse'],
    'ai-hub': ['AI Hub', 'Daily briefing, anomaly detection & performance coaching']
};
  const [title, sub] = titles[page] || [page, ''];
  document.getElementById('pageTitle').textContent = title;
  document.getElementById('pageSub').textContent = sub;

  // init charts lazily
  if (page === 'dashboard' && !State.chartsInited.dashboard) { initDashboardCharts(); State.chartsInited.dashboard = true; }
  if (page === 'sla' && !State.chartsInited.sla) { initSLACharts(); State.chartsInited.sla = true; }
  if (page === 'workload' && !State.chartsInited.workload) { initWorkloadCharts(); State.chartsInited.workload = true; }
  if (page === 'ai-hub') { setTimeout(function(){ if(typeof renderAIHub==='function') renderAIHub(); }, 100); }
}

// ── Theme ──────────────────────────────────────────────────
function toggleTheme() {
  State.darkMode = !State.darkMode;
  localStorage.setItem('sdq-dark', State.darkMode);
  applyTheme();
}
function applyTheme() {
  document.documentElement.setAttribute('data-theme', State.darkMode ? 'dark' : 'light');
  const btn = document.getElementById('themeBtn');
  if (btn) btn.innerHTML = `<i class="ti ti-${State.darkMode ? 'sun' : 'moon'}"></i>`;
}

// ── Badge ──────────────────────────────────────────────────
function updateBadge() {
  const breaches = APP_DATA.tickets.filter(t => t.status === 'SLA Breach').length;
  document.querySelectorAll('.nav-badge').forEach(b => b.textContent = breaches);
}

// ══════════════════════════════════════════════════════════
//  DASHBOARD
// ══════════════════════════════════════════════════════════
function renderDashboard() {
  const k = APP_DATA.kpis;
  setEl('kpi-total',    k.totalTickets.toLocaleString());
  setEl('kpi-resolved', k.resolved.toLocaleString());
  setEl('kpi-sla',      k.slaMet + '%');
  setEl('kpi-breaches', k.activeBreaches);
  setEl('kpi-csat',     k.csatScore + '/5');
  setEl('kpi-avgres',   k.avgResolutionHours + 'h');
  setEl('kpi-open',     k.openTickets);
  setEl('kpi-eng',      k.activeEngineers);
  renderRecentTickets();
}

function renderRecentTickets() {
  const tbody = document.getElementById('recentTicketsBody');
  if (!tbody) return;
  const recent = APP_DATA.tickets.slice(0, 8);
  tbody.innerHTML = recent.map(t => `
    <tr>
      <td><span class="td-id">#${t.id}</span></td>
      <td><div class="td-sub-text" title="${t.sub}">${t.sub}</div></td>
      <td>${t.team}</td>
      <td>${t.assignee}</td>
      <td>${priorityBadge(t.priority)}</td>
      <td>${statusBadge(t.status)}</td>
      <td>${t.updated}</td>
    </tr>`).join('');
}

// ── Dashboard Charts ───────────────────────────────────────
function initDashboardCharts() {
  const isDark = State.darkMode;
  const grid   = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';
  const ticks  = isDark ? 'rgba(255,255,255,0.4)'  : 'rgba(0,0,0,0.4)';

  // Volume bar chart
  const vc = document.getElementById('volumeChart');
  if (vc) {
    State.charts.volume = new Chart(vc, {
      type: 'bar',
      data: {
        labels: APP_DATA.volumeTrend.days,
        datasets: [
          { label: 'New',      data: APP_DATA.volumeTrend.newTickets,      backgroundColor: '#378ADD', borderRadius: 3 },
          { label: 'Resolved', data: APP_DATA.volumeTrend.resolvedTickets, backgroundColor: '#1D9E75', borderRadius: 3 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: grid }, ticks: { color: ticks, font: { size: 11 } } },
          y: { grid: { color: grid }, ticks: { color: ticks, font: { size: 11 } } }
        }
      }
    });
  }

  // Category doughnut
  const cc = document.getElementById('categoryChart');
  if (cc) {
    State.charts.category = new Chart(cc, {
      type: 'doughnut',
      data: {
        labels: APP_DATA.categoryDist.labels,
        datasets: [{ data: APP_DATA.categoryDist.values, backgroundColor: APP_DATA.categoryDist.colors, borderWidth: 0 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '68%',
        plugins: { legend: { display: false } }
      }
    });
  }
}

// ══════════════════════════════════════════════════════════
//  SLA PAGE
// ══════════════════════════════════════════════════════════
function initSLACharts() {
  const isDark = State.darkMode;
  const grid   = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';
  const ticks  = isDark ? 'rgba(255,255,255,0.4)'  : 'rgba(0,0,0,0.4)';

  // SLA trend line
  const sc = document.getElementById('slaTrendChart');
  if (sc) {
    State.charts.slaTrend = new Chart(sc, {
      type: 'line',
      data: {
        labels: APP_DATA.slaTrend.months,
        datasets: [
          {
            label: 'SLA %', data: APP_DATA.slaTrend.values,
            borderColor: '#185FA5', backgroundColor: 'rgba(24,95,165,0.1)',
            fill: true, tension: 0.4, pointBackgroundColor: '#185FA5', pointRadius: 4
          },
          {
            label: 'Target', data: Array(6).fill(APP_DATA.slaTrend.target),
            borderColor: '#A32D2D', borderDash: [5,4], pointRadius: 0, tension: 0
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: grid }, ticks: { color: ticks, font: { size: 11 } } },
          y: { min: 75, max: 100, grid: { color: grid }, ticks: { color: ticks, font: { size: 11 }, callback: v => v + '%' } }
        }
      }
    });
  }

  // SLA team bars
  const cont = document.getElementById('slaTeamBars');
  if (cont) {
    cont.innerHTML = APP_DATA.teams.map(t => {
      const clr = t.sla >= 95 ? '#1D9E75' : t.sla >= 85 ? '#378ADD' : '#E24B4A';
      return `
        <div class="sla-bar-group">
          <div class="sla-bar-label">
            <span>${t.name}</span>
            <span class="sla-bar-pct" style="color:${clr}">${t.sla}%</span>
          </div>
          <div class="sla-track">
            <div class="sla-fill" style="width:${t.sla}%;background:${clr}"></div>
          </div>
        </div>`;
    }).join('');
  }

  // SLA breach table
  const btbody = document.getElementById('slaBreachBody');
  if (btbody) {
    const breaches = APP_DATA.tickets.filter(t => t.status === 'SLA Breach');
    const overdueTimes = ['+2h 15m', '+1h 42m', '+4h 08m', '+6h 30m'];
    btbody.innerHTML = breaches.map((t, i) => `
      <tr>
        <td><span class="td-id">#${t.id}</span></td>
        <td>${t.sub}</td>
        <td>${t.team}</td>
        <td>${priorityBadge(t.priority)}</td>
        <td style="color:var(--danger);font-weight:600">${overdueTimes[i] || '+1h 00m'}</td>
        <td>${t.assignee}</td>
      </tr>`).join('');
  }
}

// ══════════════════════════════════════════════════════════
//  WORKLOAD PAGE
// ══════════════════════════════════════════════════════════
function initWorkloadCharts() {
  const isDark = State.darkMode;
  const grid   = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';
  const ticks  = isDark ? 'rgba(255,255,255,0.4)'  : 'rgba(0,0,0,0.4)';

  const wc = document.getElementById('workloadChart');
  if (wc) {
    const sorted = [...APP_DATA.teams].sort((a, b) => b.open - a.open);
    State.charts.workload = new Chart(wc, {
      type: 'bar',
      data: {
        labels: sorted.map(t => t.name),
        datasets: [{
          label: 'Open tickets',
          data: sorted.map(t => t.open),
          backgroundColor: sorted.map(t => t.badge),
          borderRadius: 4
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: grid }, ticks: { color: ticks, font: { size: 11 } } },
          y: { ticks: { color: ticks, font: { size: 12 } } }
        }
      }
    });
  }

  // Per-engineer workload bars
  const wlList = document.getElementById('wlEngineerList');
  if (wlList) {
    const allMembers = Object.values(APP_DATA.members).flat().sort((a, b) => b.open - a.open).slice(0, 12);
    const max = allMembers[0]?.open || 10;
    wlList.innerHTML = allMembers.map(m => {
      const pct = Math.round((m.open / max) * 100);
      const clr = m.wl === 'high' ? '#E24B4A' : m.wl === 'moderate' ? '#EF9F27' : '#1D9E75';
      return `<div class="wl-row">
        <div class="wl-name">${m.n}<span class="wl-badge wl-${m.wl}" title="${m.wl} workload"></span></div>
        <div class="wl-track"><div class="wl-fill" style="width:${pct}%;background:${clr}"></div></div>
        <div class="wl-count">${m.open} open</div>
      </div>`;
    }).join('');
  }

  // Top contributors table
  const ctbody = document.getElementById('contributorsBody');
  if (ctbody) {
    const top = Object.values(APP_DATA.members).flat().sort((a, b) => b.resolved - a.resolved).slice(0, 8);
    ctbody.innerHTML = top.map(m => {
      const teamEntry = Object.entries(APP_DATA.members).find(([, arr]) => arr.includes(m));
      const teamName = teamEntry ? APP_DATA.teams.find(t => t.id === teamEntry[0])?.name || '' : '';
      const slaColor = m.sla >= 95 ? 'var(--success)' : m.sla >= 85 ? 'var(--accent)' : 'var(--danger)';
      return `<tr>
        <td><div style="display:flex;align-items:center;gap:8px">
          <div class="avatar" style="width:30px;height:30px;font-size:11px;background:${getTeamColor(teamEntry?.[0])};color:${getTeamTC(teamEntry?.[0])}">${m.av}</div>
          ${m.n}</div></td>
        <td>${teamName}</td>
        <td style="color:var(--success);font-weight:600">${m.resolved}</td>
        <td>${m.open}</td>
        <td style="font-weight:600;color:${slaColor}">${m.sla}%</td>
      </tr>`;
    }).join('');
  }
}

function getTeamColor(id) { return APP_DATA.teams.find(t => t.id === id)?.color || '#eee'; }
function getTeamTC(id)    { return APP_DATA.teams.find(t => t.id === id)?.tc    || '#333'; }

// ══════════════════════════════════════════════════════════
//  TEAMS & MEMBERS
// ══════════════════════════════════════════════════════════
function renderTeamsPage() {
  const grid = document.getElementById('teamGrid');
  if (!grid) return;
  grid.innerHTML = APP_DATA.teams.map(t => `
    <div class="team-card" onclick="showTeamDetail('${t.id}')">
      <div class="team-card-header">
        <div class="team-dot" style="background:${t.badge}"></div>
        <div class="team-name">${t.name}</div>
      </div>
      <div class="team-desc">${t.desc}</div>
      <div class="team-stats">
        <div class="team-stat"><strong>${t.members}</strong>Members</div>
        <div class="team-stat"><strong>${t.open}</strong>Open</div>
        <div class="team-stat"><strong style="color:${t.sla>=90?'var(--success)':t.sla>=80?'var(--warning)':'var(--danger)'}">${t.sla}%</strong>SLA</div>
        <div class="team-stat"><strong>${t.resolved}</strong>Resolved</div>
      </div>
    </div>`).join('');
}

function showTeamDetail(tid) {
  State.currentTeam = tid;
  const t = APP_DATA.teams.find(x => x.id === tid);
  if (!t) return;
  document.getElementById('teams-list-view').style.display  = 'none';
  document.getElementById('team-detail-view').style.display = 'block';
  document.getElementById('person-detail-view').style.display = 'none';

  document.getElementById('teamDetailName').textContent = t.name;
  document.getElementById('teamDetailMeta').textContent = `${t.desc} · Lead: ${t.lead} · ${t.members} engineers`;
  document.getElementById('tdOpen').textContent     = t.open;
  document.getElementById('tdResolved').textContent = t.resolved;
  document.getElementById('tdSLA').textContent      = t.sla + '%';
  document.getElementById('tdSLA').style.color      = t.sla >= 90 ? 'var(--success)' : t.sla >= 80 ? 'var(--warning)' : 'var(--danger)';

  const ml = document.getElementById('memberList');
  ml.innerHTML = (APP_DATA.members[tid] || []).map(m => `
    <div class="member-row" onclick="showPerson('${tid}','${escapeSingle(m.n)}')">
      <div class="avatar" style="background:${t.color};color:${t.tc}">${m.av}</div>
      <div class="member-info">
        <div class="member-name">${m.n}</div>
        <div class="member-role">${m.r}</div>
      </div>
      <div class="member-right">
        <div class="member-tickets-open">${m.open} open</div>
        <div class="member-tickets-sub">${m.resolved} resolved · ${m.sla}% SLA
          <span class="wl-badge wl-${m.wl}" title="${m.wl} workload" style="display:inline-block"></span>
        </div>
      </div>
    </div>`).join('');
}

function showTeamsList() {
  document.getElementById('teams-list-view').style.display  = 'block';
  document.getElementById('team-detail-view').style.display = 'none';
  document.getElementById('person-detail-view').style.display = 'none';
}

function showPerson(tid, name) {
  const t = APP_DATA.teams.find(x => x.id === tid);
  const m = (APP_DATA.members[tid] || []).find(x => x.n === name);
  if (!t || !m) return;

  document.getElementById('team-detail-view').style.display  = 'none';
  document.getElementById('person-detail-view').style.display = 'block';
  document.getElementById('backToTeamName').textContent = t.name;

  document.getElementById('personAvatar').textContent  = m.av;
  document.getElementById('personAvatar').style.background = t.color;
  document.getElementById('personAvatar').style.color      = t.tc;
  document.getElementById('personName').textContent = m.n;
  document.getElementById('personMeta').textContent = `${m.r} · ${t.name}`;
  document.getElementById('pstatOpen').textContent     = m.open;
  document.getElementById('pstatResolved').textContent = m.resolved;
  document.getElementById('pstatSLA').textContent      = m.sla + '%';

  // Simulate latest tickets for this person
  const subs = [
    'VPN tunnel instability — user report',
    'SSL certificate renewal on proxy',
    'User account lockout investigation',
    'Firewall rule review for new subnet',
    'Switch firmware upgrade — scheduled',
    'Endpoint antivirus alert — false positive',
    'Server disk usage threshold warning'
  ];
  const statuses = ['In Progress','Open','Resolved','In Progress','Open','Resolved','Resolved'];
  const priorities = ['High','Medium','Low','Medium','High','Low','Medium'];
  const count = Math.min(m.open + 2, 5);
  const rows = Array.from({length: count}, (_, i) => `
    <tr>
      <td><span class="td-id">#TK-${1248 - i}</span></td>
      <td>${subs[i % subs.length]}</td>
      <td>${priorityBadge(priorities[i % priorities.length])}</td>
      <td>${statusBadge(statuses[i % statuses.length])}</td>
      <td>${['2m ago','1h ago','3h ago','Yesterday','2 days ago'][i]}</td>
    </tr>`).join('');

  document.getElementById('personTicketsBody').innerHTML = rows;
}

function showPersonFromTeam() {
  document.getElementById('person-detail-view').style.display = 'none';
  document.getElementById('team-detail-view').style.display   = 'block';
}

// ══════════════════════════════════════════════════════════
//  ALL TICKETS — Filter & Sort
// ══════════════════════════════════════════════════════════
function renderAllTickets() {
  let data = [...APP_DATA.tickets];
  const f = State.filters;

  if (f.status)   data = data.filter(t => t.status   === f.status);
  if (f.team)     data = data.filter(t => t.team     === f.team);
  if (f.priority) data = data.filter(t => t.priority === f.priority);
  if (f.category) data = data.filter(t => t.category === f.category);
  if (f.dateFrom) data = data.filter(t => t.created >= f.dateFrom);
  if (f.dateTo)   data = data.filter(t => t.created <= f.dateTo);
  if (f.search)   data = data.filter(t =>
    t.id.toLowerCase().includes(f.search) ||
    t.sub.toLowerCase().includes(f.search) ||
    t.assignee.toLowerCase().includes(f.search) ||
    t.team.toLowerCase().includes(f.search)
  );

  // Sort
  data.sort((a, b) => {
    let va = a[f.sort] || '', vb = b[f.sort] || '';
    if (f.sort === 'created') { va = a.created; vb = b.created; }
    const cmp = va < vb ? -1 : va > vb ? 1 : 0;
    return f.sortDir === 'asc' ? cmp : -cmp;
  });

  const tbody = document.getElementById('allTicketsBody');
  const countEl = document.getElementById('ticketResultCount');
  if (countEl) countEl.textContent = `Showing ${data.length} of ${APP_DATA.tickets.length} tickets`;

  if (!tbody) return;
  if (data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="table-empty">No tickets match the current filters.</td></tr>`;
    return;
  }
  tbody.innerHTML = data.map(t => `
    <tr>
      <td><span class="td-id">#${t.id}</span></td>
      <td class="td-sub"><div class="td-sub-text" title="${t.sub}">${t.sub}</div></td>
      <td>${t.team}</td>
      <td>${t.assignee}</td>
      <td>${priorityBadge(t.priority)}</td>
      <td>${statusBadge(t.status)}</td>
      <td>${t.created}</td>
    </tr>`).join('');
}

function applyFilter(field, val) {
  State.filters[field] = val;
  renderAllTickets();
}

function clearFilters() {
  State.filters = { status:'', team:'', priority:'', category:'', search:'', dateFrom:'', dateTo:'', sort:'created', sortDir:'desc' };
  document.querySelectorAll('.filter-select').forEach(s => s.value = '');
  document.querySelectorAll('.filter-input').forEach(i => i.value = '');
  renderAllTickets();
}

function sortTable(field) {
  if (State.filters.sort === field) {
    State.filters.sortDir = State.filters.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    State.filters.sort = field;
    State.filters.sortDir = 'desc';
  }
  renderAllTickets();
}

// ══════════════════════════════════════════════════════════
//  CREATE TICKET
// ══════════════════════════════════════════════════════════
function autoAssign() {
  const cat = document.getElementById('ct-category')?.value;
  const prev = document.getElementById('assignPreview');
  const text = document.getElementById('assignText');
  if (cat && APP_DATA.domainAssignment[cat]) {
    const team = APP_DATA.domainAssignment[cat];
    const teamData = APP_DATA.teams.find(t => t.name === team);
    if (prev) prev.style.display = 'flex';
    if (text) text.textContent = `Auto-assigned → ${team} (${teamData?.members || '?'} engineers · Lead: ${teamData?.lead || 'N/A'})`;
  } else {
    if (prev) prev.style.display = 'none';
  }
}

function clearForm() {
  ['ct-subject','ct-desc','ct-reporter','ct-email','ct-contact'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  ['ct-category','ct-priority','ct-type'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('assignPreview').style.display = 'none';
}

function submitTicket() {
  const sub = document.getElementById('ct-subject')?.value.trim();
  const cat = document.getElementById('ct-category')?.value;
  const pri = document.getElementById('ct-priority')?.value || 'Medium';
  const rep = document.getElementById('ct-reporter')?.value.trim();

  if (!sub) { showToast('Please enter a subject', 'warn'); return; }
  if (!cat)  { showToast('Please select a category', 'warn'); return; }

  APP_DATA.ticketCounter++;
  const newId = 'TK-' + APP_DATA.ticketCounter;
  const teamName = APP_DATA.domainAssignment[cat] || cat;
  const teamData = APP_DATA.teams.find(t => t.name === teamName);

  const newTicket = {
    id: newId, sub, team: teamName, teamId: teamData?.id || '',
    assignee: 'Auto-assigned', priority: pri, status: 'Open',
    category: cat, created: '2026-05-11', updated: 'Just now',
    desc: document.getElementById('ct-desc')?.value || ''
  };
  APP_DATA.tickets.unshift(newTicket);

  showToast(`✓ #${newId} created & assigned to ${teamName}`);
  clearForm();
  updateBadge();

  // Update open count
  if (teamData) {
    teamData.open++;
    APP_DATA.kpis.totalTickets++;
    APP_DATA.kpis.openTickets++;
    setEl('kpi-total', APP_DATA.kpis.totalTickets.toLocaleString());
    setEl('kpi-open', APP_DATA.kpis.openTickets);
  }
}

// ══════════════════════════════════════════════════════════
//  EXPORT — CSV
// ══════════════════════════════════════════════════════════
function exportCSV(scope) {
  let data = [];
  let filename = 'export.csv';
  let headers = [];

  if (scope === 'tickets') {
    let tickets = [...APP_DATA.tickets];
    const f = State.filters;
    if (f.status)   tickets = tickets.filter(t => t.status   === f.status);
    if (f.team)     tickets = tickets.filter(t => t.team     === f.team);
    if (f.priority) tickets = tickets.filter(t => t.priority === f.priority);
    headers = ['Ticket ID','Subject','Team','Assignee','Priority','Status','Category','Created','Updated'];
    data = tickets.map(t => [t.id, t.sub, t.team, t.assignee, t.priority, t.status, t.category, t.created, t.updated]);
    filename = 'tickets_export.csv';
  } else if (scope === 'teams') {
    headers = ['Team','Lead','Members','Open Tickets','Resolved','SLA %','Domain'];
    data = APP_DATA.teams.map(t => [t.name, t.lead, t.members, t.open, t.resolved, t.sla + '%', t.domain]);
    filename = 'teams_summary.csv';
  } else if (scope === 'sla') {
    headers = ['Team','SLA %','Open','Resolved','Members'];
    data = APP_DATA.teams.map(t => [t.name, t.sla + '%', t.open, t.resolved, t.members]);
    filename = 'sla_report.csv';
  } else if (scope === 'workload') {
    headers = ['Engineer','Role','Team','Open Tickets','Resolved','SLA %','Workload'];
    data = Object.entries(APP_DATA.members).flatMap(([tid, members]) => {
      const teamName = APP_DATA.teams.find(t => t.id === tid)?.name || tid;
      return members.map(m => [m.n, m.r, teamName, m.open, m.resolved, m.sla + '%', m.wl]);
    });
    filename = 'workload_export.csv';
  }

  const csvLines = [headers, ...data].map(row =>
    row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
  ).join('\n');

  const blob = new Blob([csvLines], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`✓ ${filename} downloaded`);
}

// ══════════════════════════════════════════════════════════
//  EXPORT — PDF (via print)
// ══════════════════════════════════════════════════════════
function exportPDF(scope) {
  const titles = {
    dashboard: 'Executive Dashboard Report',
    sla:       'SLA Monitor Report',
    workload:  'Team Workload Report',
    teams:     'Teams & Members Report',
    tickets:   'All Tickets Report'
  };
  const title = titles[scope] || 'ServiceDesk Report';
  const date  = new Date().toLocaleDateString('en-IN', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
  const k = APP_DATA.kpis;

  let content = '';
  if (scope === 'dashboard' || scope === 'summary') {
    content = `
      <h2>Key Performance Indicators</h2>
      <table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;margin-bottom:20px">
        <tr style="background:#f0f0f0"><th>Metric</th><th>Value</th><th>Note</th></tr>
        <tr><td>Total Tickets</td><td>${k.totalTickets.toLocaleString()}</td><td>All time</td></tr>
        <tr><td>Resolved</td><td>${k.resolved.toLocaleString()}</td><td>${k.resolutionRate}% resolution rate</td></tr>
        <tr><td>SLA Met</td><td>${k.slaMet}%</td><td>Target: 95%</td></tr>
        <tr><td>Active SLA Breaches</td><td>${k.activeBreaches}</td><td>Requires attention</td></tr>
        <tr><td>CSAT Score</td><td>${k.csatScore}/5</td><td></td></tr>
        <tr><td>Avg Resolution Time</td><td>${k.avgResolutionHours}h</td><td></td></tr>
        <tr><td>Active Engineers</td><td>${k.activeEngineers}</td><td>Across 7 teams</td></tr>
      </table>
      <h2>Team Performance</h2>
      <table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse">
        <tr style="background:#f0f0f0"><th>Team</th><th>Lead</th><th>Members</th><th>Open</th><th>Resolved</th><th>SLA %</th></tr>
        ${APP_DATA.teams.map(t => `<tr><td>${t.name}</td><td>${t.lead}</td><td>${t.members}</td><td>${t.open}</td><td>${t.resolved}</td><td>${t.sla}%</td></tr>`).join('')}
      </table>`;
  } else if (scope === 'tickets') {
    let tickets = [...APP_DATA.tickets];
    const f = State.filters;
    if (f.status)   tickets = tickets.filter(t => t.status   === f.status);
    if (f.team)     tickets = tickets.filter(t => t.team     === f.team);
    if (f.priority) tickets = tickets.filter(t => t.priority === f.priority);
    content = `
      <h2>Tickets (${tickets.length} shown)</h2>
      <table border="1" cellpadding="6" cellspacing="0" style="width:100%;border-collapse:collapse;font-size:11px">
        <tr style="background:#f0f0f0"><th>ID</th><th>Subject</th><th>Team</th><th>Assignee</th><th>Priority</th><th>Status</th><th>Created</th></tr>
        ${tickets.map(t => `<tr><td>${t.id}</td><td>${t.sub}</td><td>${t.team}</td><td>${t.assignee}</td><td>${t.priority}</td><td>${t.status}</td><td>${t.created}</td></tr>`).join('')}
      </table>`;
  } else if (scope === 'sla') {
    content = `
      <h2>SLA Summary</h2>
      <table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse">
        <tr style="background:#f0f0f0"><th>Team</th><th>SLA %</th><th>Status</th><th>Open</th><th>Resolved</th></tr>
        ${APP_DATA.teams.map(t => `<tr><td>${t.name}</td><td>${t.sla}%</td><td>${t.sla>=95?'✓ On Track':t.sla>=85?'⚠ Monitor':'✗ At Risk'}</td><td>${t.open}</td><td>${t.resolved}</td></tr>`).join('')}
      </table>
      <h2>SLA Breached Tickets</h2>
      <table border="1" cellpadding="6" cellspacing="0" style="width:100%;border-collapse:collapse">
        <tr style="background:#f0f0f0"><th>Ticket ID</th><th>Subject</th><th>Team</th><th>Assignee</th><th>Priority</th></tr>
        ${APP_DATA.tickets.filter(t=>t.status==='SLA Breach').map(t=>`<tr><td>${t.id}</td><td>${t.sub}</td><td>${t.team}</td><td>${t.assignee}</td><td>${t.priority}</td></tr>`).join('')}
      </table>`;
  }

  const win = window.open('', '_blank');
  win.document.write(`<!DOCTYPE html><html><head>
    <title>${title}</title>
    <style>
      body{font-family:Arial,sans-serif;padding:30px;font-size:13px;color:#222}
      h1{font-size:20px;margin-bottom:4px;color:#185FA5}
      h2{font-size:15px;margin:20px 0 8px;color:#333;border-bottom:1px solid #ddd;padding-bottom:4px}
      .meta{font-size:12px;color:#666;margin-bottom:20px}
      table{font-size:12px}
      th{text-align:left;background:#f0f0f0}
      @media print{button{display:none}}
    </style>
  </head><body>
    <h1>ServiceDesk HQ — ${title}</h1>
    <div class="meta">Project ATLAS &nbsp;|&nbsp; Generated: ${date} &nbsp;|&nbsp; ${k.activeEngineers} engineers · ${k.totalTickets} tickets</div>
    <button onclick="window.print()" style="padding:8px 16px;background:#185FA5;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;margin-bottom:20px">🖨 Print / Save as PDF</button>
    ${content}
  </body></html>`);
  win.document.close();
  showToast('PDF preview opened in new tab');
}

// ══════════════════════════════════════════════════════════
//  AI ASSISTANT
// ══════════════════════════════════════════════════════════
function toggleAI() {
  State.aiOpen = !State.aiOpen;
  document.getElementById('aiPanel').classList.toggle('open', State.aiOpen);
  if (State.aiOpen) setTimeout(() => document.getElementById('aiInput')?.focus(), 300);
}

function askAI(q) {
  document.getElementById('aiInput').value = q;
  sendAI();
}

async function sendAI() {
  const inp = document.getElementById('aiInput');
  const q = inp?.value.trim();
  if (!q) return;

  const msgs = document.getElementById('aiMessages');
  msgs.innerHTML += `<div class="msg user">${escapeHTML(q)}</div>`;
  inp.value = '';

  const typing = document.createElement('div');
  typing.className = 'msg-typing'; typing.id = 'typing';
  typing.innerHTML = '<div class="dot-anim"></div><div class="dot-anim"></div><div class="dot-anim"></div>';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;

  try {
    const result = await api.aiChat(q, State.aiHistory || []);
    document.getElementById('typing')?.remove();
    msgs.innerHTML += `<div class="msg ai">${escapeHTML(result.reply)}</div>`;
    State.aiHistory = State.aiHistory || [];
    State.aiHistory.push({ role: 'user', content: q });
    State.aiHistory.push({ role: 'assistant', content: result.reply });
  } catch (e) {
    document.getElementById('typing')?.remove();
    msgs.innerHTML += `<div class="msg ai">Error: ${e.message}</div>`;
  }
  msgs.scrollTop = msgs.scrollHeight;
}
// ══════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════
function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function escapeSingle(s) { return (s || '').replace(/'/g, "\\'"); }
function escapeHTML(s)    { return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function statusBadge(s) {
  const map = {
    'Open': 'badge-open', 'In Progress': 'badge-progress',
    'Resolved': 'badge-resolved', 'SLA Breach': 'badge-breach'
  };
  return `<span class="badge ${map[s] || 'badge-open'}">${s}</span>`;
}

function priorityBadge(p) {
  const map = { 'High':'badge-high','Medium':'badge-medium','Low':'badge-low','Critical':'badge-critical' };
  return `<span class="badge ${map[p] || 'badge-medium'}">${p}</span>`;
}

function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = type === 'warn' ? '#BA7517' : '#0F6E56';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3500);
}
function showAIHub() {
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  document.querySelector('[data-page="ai-hub"]').classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  const hub = document.getElementById('page-ai-hub');
  hub.style.display = 'block';
  hub.style.padding = '20px';
  State.currentPage = 'ai-hub';
  document.getElementById('pageTitle').textContent = 'AI Hub';
  document.getElementById('pageSub').textContent = 'Daily briefing, anomaly detection & performance coaching';
  if (typeof renderAIHub === 'function') renderAIHub();
}
