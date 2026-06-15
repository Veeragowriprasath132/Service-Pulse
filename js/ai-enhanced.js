/**
 * ai-enhanced.js — Enhanced AI Features for ServicePulse
 * 1. AI Daily Briefing
 * 2. AI Ticket Summarizer
 * 3. AI Performance Coach
 * 4. AI Anomaly Detector
 */

const AI_BACKEND = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://service-pulse-xzsh.onrender.com';

// ══════════════════════════════════════════════════════════
// 1. AI DAILY BRIEFING
// ══════════════════════════════════════════════════════════

async function loadDailyBriefing() {
  const container = document.getElementById('dailyBriefing');
  if (!container) return;

  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;padding:16px;color:var(--text-muted)">
      <div class="dot-anim" style="width:8px;height:8px;border-radius:50%;background:var(--accent);animation:bounce 1.2s infinite"></div>
      <span style="font-size:13px">AI is generating your daily briefing...</span>
    </div>`;

  try {
    const res  = await fetch(`${AI_BACKEND}/api/ai/daily-briefing`);
    const data = await res.json();

    const severityColors = {
      high:   { bg: '#FCEBEB', border: '#F5B7B7', icon: '🔴' },
      medium: { bg: '#FAEEDA', border: '#F5D87A', icon: '🟡' },
      low:    { bg: '#EAF3DE', border: '#B5D9C8', icon: '🟢' },
    };

    const breachCount = data.alerts?.sla_breach_count || 0;
    const severity    = breachCount > 10 ? 'high' : breachCount > 5 ? 'medium' : 'low';
    const sc          = severityColors[severity];

    container.innerHTML = `
      <div style="background:${sc.bg};border:1px solid ${sc.border};border-radius:10px;padding:16px;margin-bottom:12px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <div style="font-size:14px;font-weight:600;color:var(--text-primary)">
            ${sc.icon} AI Daily Briefing — ${data.date}
          </div>
          <button onclick="loadDailyBriefing()" style="background:none;border:none;cursor:pointer;color:var(--text-muted);font-size:13px">
            <i class="ti ti-refresh"></i> Refresh
          </button>
        </div>
        <div style="font-size:13px;color:var(--text-primary);line-height:1.7;white-space:pre-wrap">${formatAIText(data.briefing)}</div>
        ${data.alerts?.teams_at_risk?.length ? `
          <div style="margin-top:10px;padding:8px 12px;background:rgba(163,45,45,0.08);border-radius:6px;font-size:12px;color:#A32D2D">
            ⚠️ Teams needing attention: <strong>${data.alerts.teams_at_risk.join(', ')}</strong>
          </div>` : ''}
      </div>`;
  } catch (e) {
    container.innerHTML = `<div style="color:var(--danger);font-size:13px;padding:12px">Failed to generate briefing. ${e.message}</div>`;
  }
}


// ══════════════════════════════════════════════════════════
// 2. AI TICKET SUMMARIZER
// ══════════════════════════════════════════════════════════

async function summarizeTicket(ticketData) {
  const modal = document.getElementById('aiSummaryModal');
  const body  = document.getElementById('aiSummaryBody');
  if (!modal || !body) {
    createAISummaryModal();
    return summarizeTicket(ticketData);
  }

  modal.classList.add('open');
  body.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;padding:20px;color:var(--text-muted)">
      <div style="width:20px;height:20px;border:2px solid var(--accent);border-top-color:transparent;border-radius:50%;animation:spin 0.7s linear infinite"></div>
      <span>AI is analyzing ticket #${ticketData.id}...</span>
    </div>`;

  document.getElementById('aiSummaryTitle').textContent = `AI Analysis — ${ticketData.ticket_number || '#' + ticketData.id}`;

  try {
    const res  = await fetch(`${AI_BACKEND}/api/ai/summarize-ticket`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticket_id:     ticketData.id,
        subject:       ticketData.subject,
        description:   ticketData.description,
        category:      ticketData.category,
        priority:      ticketData.priority,
        status:        ticketData.status,
        team_name:     ticketData.team_name,
        assignee_name: ticketData.assignee_name,
        created_at:    ticketData.created_at,
        sla_due_at:    ticketData.sla_due_at,
      })
    });
    const data = await res.json();

    body.innerHTML = `
      <div style="padding:4px 0">
        <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap">
          ${priorityBadge ? priorityBadge(data.priority) : `<span>${data.priority}</span>`}
          ${statusBadge   ? statusBadge(data.status)     : `<span>${data.status}</span>`}
          <span style="font-size:12px;color:var(--text-muted)">Generated ${new Date().toLocaleTimeString()}</span>
        </div>
        <div style="font-size:13px;color:var(--text-primary);line-height:1.8;white-space:pre-wrap">${formatAIText(data.summary)}</div>
      </div>`;
  } catch (e) {
    body.innerHTML = `<div style="color:var(--danger);font-size:13px;padding:12px">Analysis failed: ${e.message}</div>`;
  }
}

function createAISummaryModal() {
  if (document.getElementById('aiSummaryModal')) return;
  const modal = document.createElement('div');
  modal.id = 'aiSummaryModal';
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal" style="max-width:620px">
      <div class="modal-header" style="background:linear-gradient(135deg,#0C447C,#185FA5);border-radius:var(--radius-lg) var(--radius-lg) 0 0">
        <div style="display:flex;align-items:center;gap:10px">
          <i class="ti ti-robot" style="font-size:20px;color:#fff"></i>
          <div class="modal-title" style="color:#fff" id="aiSummaryTitle">AI Ticket Analysis</div>
        </div>
        <button class="modal-close" onclick="document.getElementById('aiSummaryModal').classList.remove('open')" style="color:rgba(255,255,255,0.8)">
          <i class="ti ti-x"></i>
        </button>
      </div>
      <div class="modal-body" id="aiSummaryBody" style="max-height:450px;overflow-y:auto"></div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="document.getElementById('aiSummaryModal').classList.remove('open')">Close</button>
      </div>
    </div>`;
  document.body.appendChild(modal);
}


// ══════════════════════════════════════════════════════════
// 3. AI PERFORMANCE COACH
// ══════════════════════════════════════════════════════════

async function loadPerformanceCoach() {
  const container = document.getElementById('performanceCoach');
  if (!container) return;

  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;padding:16px;color:var(--text-muted)">
      <div style="width:16px;height:16px;border:2px solid var(--accent);border-top-color:transparent;border-radius:50%;animation:spin 0.7s linear infinite"></div>
      <span style="font-size:13px">Performance Coach is analyzing your teams...</span>
    </div>`;

  try {
    const res  = await fetch(`${AI_BACKEND}/api/ai/performance-coach`);
    const data = await res.json();

    container.innerHTML = `
      <div style="margin-bottom:14px">
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px">
          <div style="background:var(--brand-light);border-radius:8px;padding:8px 14px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:var(--brand)">${data.summary.total_teams}</div>
            <div style="font-size:11px;color:var(--text-muted)">Teams</div>
          </div>
          <div style="background:#FCEBEB;border-radius:8px;padding:8px 14px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:var(--danger)">${data.summary.teams_at_risk}</div>
            <div style="font-size:11px;color:var(--text-muted)">At Risk</div>
          </div>
          <div style="background:#FAEEDA;border-radius:8px;padding:8px 14px;text-align:center">
            <div style="font-size:20px;font-weight:700;color:var(--warning)">${data.summary.avg_load_overall}</div>
            <div style="font-size:11px;color:var(--text-muted)">Avg Load</div>
          </div>
        </div>
        <div style="font-size:13px;color:var(--text-primary);line-height:1.8;white-space:pre-wrap">${formatAIText(data.coaching_report)}</div>
      </div>`;
  } catch (e) {
    container.innerHTML = `<div style="color:var(--danger);font-size:13px;padding:12px">Coach unavailable: ${e.message}</div>`;
  }
}


// ══════════════════════════════════════════════════════════
// 4. AI ANOMALY DETECTOR
// ══════════════════════════════════════════════════════════

async function loadAnomalyDetector() {
  const container = document.getElementById('anomalyDetector');
  if (!container) return;

  try {
    const res  = await fetch(`${AI_BACKEND}/api/ai/anomalies`);
    const data = await res.json();

    const icons = { critical: '🔴', warning: '🟡', normal: '🟢' };
    const bgs   = { critical: '#FCEBEB', warning: '#FAEEDA', normal: '#EAF3DE' };
    const borders = { critical: '#F5B7B7', warning: '#F5D87A', normal: '#B5D9C8' };

    container.innerHTML = `
      <div style="background:${bgs[data.severity]};border:1px solid ${borders[data.severity]};border-radius:10px;padding:14px">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
          <div style="font-size:14px;font-weight:600;color:var(--text-primary)">
            ${icons[data.severity]} Anomaly Status: <span style="color:${data.severity_color};text-transform:capitalize">${data.severity}</span>
          </div>
          <div style="font-size:12px;color:var(--text-muted)">${data.anomaly_count} signals detected</div>
        </div>
        ${data.anomalies_found.length ? `
          <div style="margin-bottom:10px">
            ${data.anomalies_found.map(a => `
              <div style="font-size:12px;padding:5px 8px;background:rgba(163,45,45,0.08);border-radius:4px;margin-bottom:4px;color:#A32D2D">
                ⚠️ ${a}
              </div>`).join('')}
          </div>` : ''}
        <div style="font-size:13px;color:var(--text-primary);line-height:1.7;white-space:pre-wrap">${formatAIText(data.report)}</div>
      </div>`;

    // Update notification badge
    if (data.severity === 'critical') {
      const badge = document.getElementById('anomalyBadge');
      if (badge) { badge.textContent = data.anomaly_count; badge.style.display = 'inline'; }
    }
  } catch (e) {
    container.innerHTML = `<div style="color:var(--danger);font-size:13px;padding:12px">Detector unavailable: ${e.message}</div>`;
  }
}


// ══════════════════════════════════════════════════════════
// AI HUB PAGE — shows all 4 features
// ══════════════════════════════════════════════════════════

function renderAIHub() {
  const content = document.getElementById('page-ai-hub');
  if (!content) return;

  content.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <div>
        <div style="font-size:20px;font-weight:700;color:var(--text-primary)">🤖 AI Intelligence Hub</div>
        <div style="font-size:13px;color:var(--text-muted);margin-top:2px">Powered by Groq LLaMA3 + RAG Pipeline</div>
      </div>
      <button class="btn btn-primary btn-sm" onclick="refreshAllAI()">
        <i class="ti ti-refresh"></i> Refresh All
      </button>
    </div>

    <!-- Daily Briefing -->
    <div class="card" style="margin-bottom:16px">
      <div class="card-header-bar" style="background:linear-gradient(135deg,#0C447C,#185FA5);border-radius:var(--radius-lg) var(--radius-lg) 0 0">
        <div style="display:flex;align-items:center;gap:8px">
          <i class="ti ti-sun" style="font-size:18px;color:#fff"></i>
          <div>
            <div style="font-size:14px;font-weight:600;color:#fff">AI Daily Briefing</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.65)">Auto-generated executive summary</div>
          </div>
        </div>
        <button onclick="loadDailyBriefing()" class="btn btn-sm" style="background:rgba(255,255,255,0.15);color:#fff;border:none">
          <i class="ti ti-refresh"></i> Regenerate
        </button>
      </div>
      <div class="card-body" id="dailyBriefing">
        <div style="color:var(--text-muted);font-size:13px;padding:8px">Click Regenerate to get today's briefing.</div>
      </div>
    </div>

    <!-- Anomaly Detector + Performance Coach side by side -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">

      <!-- Anomaly Detector -->
      <div class="card">
        <div class="card-header-bar">
          <div style="display:flex;align-items:center;gap:8px">
            <i class="ti ti-radar" style="font-size:18px;color:var(--danger)"></i>
            <div>
              <div class="card-title">Anomaly Detector</div>
              <div class="card-sub">Real-time pattern analysis</div>
            </div>
          </div>
          <button onclick="loadAnomalyDetector()" class="btn btn-secondary btn-sm">
            <i class="ti ti-refresh"></i> Scan
          </button>
        </div>
        <div class="card-body" id="anomalyDetector">
          <div style="color:var(--text-muted);font-size:13px">Click Scan to detect anomalies.</div>
        </div>
      </div>

      <!-- Performance Coach -->
      <div class="card">
        <div class="card-header-bar">
          <div style="display:flex;align-items:center;gap:8px">
            <i class="ti ti-chart-line" style="font-size:18px;color:var(--success)"></i>
            <div>
              <div class="card-title">Performance Coach</div>
              <div class="card-sub">Team health & recommendations</div>
            </div>
          </div>
          <button onclick="loadPerformanceCoach()" class="btn btn-secondary btn-sm">
            <i class="ti ti-refresh"></i> Analyze
          </button>
        </div>
        <div class="card-body" id="performanceCoach">
          <div style="color:var(--text-muted);font-size:13px">Click Analyze to get coaching insights.</div>
        </div>
      </div>
    </div>

    <!-- AI Chat Assistant -->
    <div class="card">
      <div class="card-header-bar">
        <div style="display:flex;align-items:center;gap:8px">
          <i class="ti ti-message-chatbot" style="font-size:18px;color:var(--brand)"></i>
          <div>
            <div class="card-title">AI Assistant</div>
            <div class="card-sub">Ask anything about your service desk</div>
          </div>
        </div>
      </div>
      <div class="card-body">
        <div id="aiHubMessages" style="min-height:150px;max-height:280px;overflow-y:auto;margin-bottom:12px;display:flex;flex-direction:column;gap:8px">
          <div style="background:var(--bg-secondary);border-radius:10px;padding:10px 14px;font-size:13px;color:var(--text-primary);max-width:85%;align-self:flex-start">
            Hello! I'm your ServiceDesk AI. Ask me about tickets, SLAs, team performance, or any aspect of Project ATLAS.
          </div>
        </div>
        <div style="display:flex;gap:8px">
          <input id="aiHubInput" class="form-input" placeholder="Ask about SLA trends, team performance, ticket patterns..."
            onkeydown="if(event.key==='Enter')sendAIHubMessage()" style="flex:1" />
          <button class="btn btn-primary" onclick="sendAIHubMessage()">
            <i class="ti ti-send"></i> Send
          </button>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">
          ${['Which team needs urgent attention?','Summarize overall project health','What are the top SLA risks today?','Which engineer is most overloaded?'].map(q =>
            `<button class="btn btn-secondary btn-sm" style="font-size:11px" onclick="document.getElementById('aiHubInput').value='${q}';sendAIHubMessage()">${q}</button>`
          ).join('')}
        </div>
      </div>
    </div>
  `;

  // Auto-load briefing and anomalies
  setTimeout(() => {
    loadDailyBriefing();
    loadAnomalyDetector();
  }, 500);
}

async function sendAIHubMessage() {
  const input    = document.getElementById('aiHubInput');
  const messages = document.getElementById('aiHubMessages');
  const q = input?.value.trim();
  if (!q || !messages) return;

  messages.innerHTML += `<div style="background:var(--brand);color:#fff;border-radius:10px;padding:10px 14px;font-size:13px;max-width:85%;align-self:flex-end;margin-left:auto">${q}</div>`;
  input.value = '';

  const typing = document.createElement('div');
  typing.id = 'aiHubTyping';
  typing.style.cssText = 'background:var(--bg-secondary);border-radius:10px;padding:10px 14px;display:flex;gap:4px;align-self:flex-start';
  typing.innerHTML = '<div style="width:6px;height:6px;border-radius:50%;background:var(--text-muted);animation:bounce 1.2s infinite"></div>'.repeat(3);
  messages.appendChild(typing);
  messages.scrollTop = messages.scrollHeight;

  try {
    const res  = await fetch(`${AI_BACKEND}/api/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: q, history: [] })
    });
    const data = await res.json();
    document.getElementById('aiHubTyping')?.remove();
    messages.innerHTML += `<div style="background:var(--bg-secondary);border-radius:10px;padding:10px 14px;font-size:13px;color:var(--text-primary);max-width:85%;align-self:flex-start;line-height:1.6">${data.reply}</div>`;
  } catch (e) {
    document.getElementById('aiHubTyping')?.remove();
    messages.innerHTML += `<div style="color:var(--danger);font-size:13px;padding:8px">Error: ${e.message}</div>`;
  }
  messages.scrollTop = messages.scrollHeight;
}

function refreshAllAI() {
  loadDailyBriefing();
  loadAnomalyDetector();
  loadPerformanceCoach();
}


// ── Helper: format AI markdown-like text ──────────────────
function formatAIText(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^#{1,3}\s(.+)$/gm, '<div style="font-weight:700;color:var(--text-primary);margin-top:10px;margin-bottom:4px">$1</div>')
    .replace(/^-\s(.+)$/gm, '<div style="padding-left:16px">• $1</div>')
    .replace(/^\d+\.\s(.+)$/gm, '<div style="padding-left:16px;margin-bottom:2px">$&</div>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}
