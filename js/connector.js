/**
 * connector.js — Universal API Connector for ServicePulse
 * Add this file to frontend/js/ and include in index.html
 */

const BACKEND = 'https://service-pulse-xzsh.onrender.com';

// ── Endpoint presets per system type ─────────────────────
const ENDPOINT_PRESETS = {
  ticketflow:       { tickets: '/api/tickets', summary: '/api/summary', sync: '/api/sync' },
  jira:             { tickets: '/rest/api/3/search', summary: '/rest/api/3/project', sync: '/rest/api/3/search' },
  freshservice:     { tickets: '/api/v2/tickets', summary: '/api/v2/tickets?per_page=1', sync: '/api/v2/tickets' },
  zendesk:          { tickets: '/api/v2/tickets.json', summary: '/api/v2/tickets/count.json', sync: '/api/v2/tickets.json' },
  servicedesk_plus: { tickets: '/api/v3/requests', summary: '/api/v3/requests?page_size=1', sync: '/api/v3/requests' },
  custom:           { tickets: '/api/tickets', summary: '/api/summary', sync: '/api/sync' },
};

function autoFillEndpoints() {
  const type = document.getElementById('conn-type').value;
  const preset = ENDPOINT_PRESETS[type] || ENDPOINT_PRESETS.custom;
  document.getElementById('conn-tickets-ep').value = preset.tickets;
  document.getElementById('conn-summary-ep').value = preset.summary;

  // Auto-fill URL placeholder based on type
  const placeholders = {
    ticketflow:       'https://ticketflow-g671.onrender.com',
    jira:             'https://yourcompany.atlassian.net',
    freshservice:     'https://yourcompany.freshservice.com',
    zendesk:          'https://yourcompany.zendesk.com',
    servicedesk_plus: 'https://helpdesk.yourcompany.com',
    custom:           'https://your-ticketing-system.com',
  };
  document.getElementById('conn-url').placeholder = placeholders[type] || 'https://your-system.com';
}

function toggleApiKey() {
  const auth = document.getElementById('conn-auth').value;
  document.getElementById('apiKeyGroup').style.display = auth !== 'none' ? 'block' : 'none';
}

function clearConnectorForm() {
  ['conn-name','conn-url','conn-apikey'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('connTestResult').innerHTML = '';
}

// ── Test connection before adding ─────────────────────────
async function testNewConnection() {
  const url = document.getElementById('conn-url').value.trim();
  const result = document.getElementById('connTestResult');
  if (!url) { result.innerHTML = '<div style="color:var(--danger);font-size:13px">Please enter a URL first.</div>'; return; }

  result.innerHTML = '<div style="font-size:13px;color:var(--text-muted)">⏳ Testing connection...</div>';

  try {
    const res = await fetch(`${url}/health`);
    const data = await res.json();
    result.innerHTML = `
      <div style="background:var(--success-bg);border:1px solid #B5D9C8;border-radius:8px;padding:10px 14px;font-size:13px">
        <strong style="color:var(--success)">✅ Connection successful!</strong><br/>
        <span style="color:var(--text-secondary)">App: ${data.app || 'Unknown'} · Status: ${data.status || 'ok'}</span>
      </div>`;
  } catch (e) {
    result.innerHTML = `
      <div style="background:var(--danger-bg);border:1px solid #F5B7B7;border-radius:8px;padding:10px 14px;font-size:13px">
        <strong style="color:var(--danger)">❌ Connection failed</strong><br/>
        <span style="color:var(--text-secondary)">${e.message}</span>
      </div>`;
  }
}

// ── Add connector via backend ─────────────────────────────
async function addConnector() {
  const name    = document.getElementById('conn-name').value.trim();
  const url     = document.getElementById('conn-url').value.trim();
  const type    = document.getElementById('conn-type').value;
  const auth    = document.getElementById('conn-auth').value;
  const apikey  = document.getElementById('conn-apikey').value.trim();
  const tep     = document.getElementById('conn-tickets-ep').value.trim();
  const sep     = document.getElementById('conn-summary-ep').value.trim();

  if (!name || !url) { showToast('Please fill name and URL', 'warn'); return; }

  try {
    const res = await fetch(`${BACKEND}/api/connectors`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, base_url: url, auth_type: auth,
        api_key: apikey || null,
        tickets_endpoint: tep,
        summary_endpoint: sep,
        sync_endpoint: '/api/sync',
        auto_sync: true
      })
    });
    const connector = await res.json();
    showToast(`✓ ${name} connected!`);
    clearConnectorForm();
    loadConnectors();

    // Auto-sync after adding
    setTimeout(() => syncConnector(connector.id), 1000);
  } catch (e) {
    showToast('Failed to add connector', 'error');
  }
}

// ── Load connectors list ───────────────────────────────────
async function loadConnectors() {
  try {
    const res = await fetch(`${BACKEND}/api/connectors`);
    const connectors = await res.json();
    const container = document.getElementById('connectorsList');

    if (connectors.length === 0) {
      container.innerHTML = `<div style="text-align:center;padding:30px;color:var(--text-muted);font-size:13px">No connectors added yet. Add your first ticketing system above!</div>`;
      return;
    }

    container.innerHTML = connectors.map(c => `
      <div style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;background:var(--bg-primary)">
        <div style="width:10px;height:10px;border-radius:50%;background:${c.status === 'connected' ? 'var(--success)' : c.status === 'error' ? 'var(--danger)' : 'var(--warning)'}"></div>
        <div style="flex:1">
          <div style="font-size:13px;font-weight:600;color:var(--text-primary)">${c.name}</div>
          <div style="font-size:11px;color:var(--text-muted)">${c.base_url} · ${c.ticket_count} tickets · Last sync: ${c.last_sync ? new Date(c.last_sync).toLocaleTimeString() : 'Never'}</div>
          ${c.last_error ? `<div style="font-size:11px;color:var(--danger)">${c.last_error}</div>` : ''}
        </div>
        <button class="topbar-btn" onclick="syncConnector('${c.id}')" style="font-size:12px;display:flex;align-items:center;gap:4px">
          <i class="ti ti-refresh" style="font-size:13px"></i>Sync
        </button>
        <button class="topbar-btn" onclick="viewConnectorTickets('${c.id}')" style="font-size:12px;display:flex;align-items:center;gap:4px">
          <i class="ti ti-eye" style="font-size:13px"></i>View
        </button>
        <button onclick="removeConnector('${c.id}')" style="background:none;border:none;cursor:pointer;color:var(--danger);font-size:16px;padding:4px">
          <i class="ti ti-trash"></i>
        </button>
      </div>`).join('');
  } catch (e) {
    console.error('Failed to load connectors:', e);
  }
}

// ── Sync a connector ──────────────────────────────────────
async function syncConnector(connectorId) {
  showToast('⏳ Syncing...');
  try {
    const res = await fetch(`${BACKEND}/api/connectors/${connectorId}/sync`, { method: 'POST' });
    const data = await res.json();
    showToast(`✓ Synced ${data.count} tickets from ${data.source}`);
    loadConnectors();
    viewConnectorTickets(connectorId);
  } catch (e) {
    showToast('Sync failed: ' + e.message, 'error');
  }
}

// ── Sync all connectors ───────────────────────────────────
async function syncAllConnectors() {
  try {
    const res  = await fetch(`${BACKEND}/api/connectors`);
    const list = await res.json();
    for (const c of list) {
      await syncConnector(c.id);
    }
    showToast(`✓ All ${list.length} connectors synced!`);
  } catch (e) {
    showToast('Sync all failed', 'error');
  }
}

// ── View tickets from a connector ────────────────────────
async function viewConnectorTickets(connectorId) {
  try {
    const res  = await fetch(`${BACKEND}/api/connectors/${connectorId}/tickets`);
    const data = await res.json();

    document.getElementById('syncedTicketsCard').style.display = 'block';
    document.getElementById('syncedTicketsSub').textContent =
      `${data.count} tickets from ${data.source} · Last sync: ${data.last_sync ? new Date(data.last_sync).toLocaleTimeString() : 'Never'}`;

    const tbody = document.getElementById('syncedTicketsBody');
    if (!data.tickets || data.tickets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:20px;color:var(--text-muted)">No tickets synced yet. Click Sync first.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.tickets.map(t => `
      <tr>
        <td style="color:var(--accent);font-weight:600;font-size:12px">${t.id}</td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.subject}</td>
        <td>${t.team_name || '—'}</td>
        <td>${t.assignee_name || '—'}</td>
        <td>${priorityBadge(t.priority)}</td>
        <td>${statusBadge(t.status)}</td>
        <td><span style="background:var(--accent-light);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">${t.source}</span></td>
      </tr>`).join('');

    // Scroll to tickets
    document.getElementById('syncedTicketsCard').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    showToast('Failed to load tickets', 'error');
  }
}

// ── Remove connector ──────────────────────────────────────
async function removeConnector(connectorId) {
  if (!confirm('Remove this connector?')) return;
  await fetch(`${BACKEND}/api/connectors/${connectorId}`, { method: 'DELETE' });
  showToast('Connector removed');
  loadConnectors();
  document.getElementById('syncedTicketsCard').style.display = 'none';
}

// ── Load on page open ─────────────────────────────────────
// Called when user navigates to connectors page
function initConnectorsPage() {
  autoFillEndpoints();
  loadConnectors();
}
