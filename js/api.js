/**
 * js/api.js — Frontend API client
 * All calls to the FastAPI backend go through this module.
 */

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `http://${window.location.hostname}:8000`
  : 'https://service-pulse-xzsh.onrender.com';   // same origin if served by FastAPI

class APIClient {
  constructor(base = API_BASE) {
    this.base = base;
  }

  async _request(path, options = {}) {
    const url = `${this.base}${path}`;
    try {
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return res.status === 204 ? null : await res.json();
    } catch (e) {
      console.error(`[API] ${options.method || 'GET'} ${path} →`, e.message);
      throw e;
    }
  }

  // ── Dashboard ────────────────────────────────────────
  getDashboardSummary()      { return this._request('/api/dashboard/summary'); }
  getKPIs()                  { return this._request('/api/dashboard/kpis'); }
  getSLA()                   { return this._request('/api/dashboard/sla'); }
  getWorkload()              { return this._request('/api/dashboard/workload'); }
  getTrends(days = 7)        { return this._request(`/api/dashboard/trends?days=${days}`); }

  // ── Tickets ──────────────────────────────────────────
  getTickets(params = {}) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([,v]) => v !== '' && v != null))
    ).toString();
    return this._request(`/api/tickets${qs ? '?' + qs : ''}`);
  }

  createTicket(data) {
    return this._request('/api/tickets', {
      method: 'POST', body: JSON.stringify(data)
    });
  }

  getTicket(id)  { return this._request(`/api/tickets/${id}`); }

  updateTicket(id, data) {
    return this._request(`/api/tickets/${id}`, {
      method: 'PATCH', body: JSON.stringify(data)
    });
  }

  deleteTicket(id) {
    return this._request(`/api/tickets/${id}`, { method: 'DELETE' });
  }

  // ── Teams ────────────────────────────────────────────
  getTeams()                       { return this._request('/api/teams'); }
  getTeamMembers(teamId)           { return this._request(`/api/teams/${teamId}/members`); }
  getTeamTickets(teamId, params={}) {
    const qs = new URLSearchParams(params).toString();
    return this._request(`/api/teams/${teamId}/tickets${qs ? '?' + qs : ''}`);
  }
  getMemberTickets(teamId, memberId, params={}) {
    const qs = new URLSearchParams(params).toString();
    return this._request(`/api/teams/${teamId}/members/${memberId}/tickets${qs ? '?' + qs : ''}`);
  }

  // ── AI ───────────────────────────────────────────────
  aiChat(message, history = []) {
    return this._request('/api/ai/chat', {
      method: 'POST', body: JSON.stringify({ message, history })
    });
  }

  aiRoute(subject, description='', category='') {
    return this._request('/api/ai/route', {
      method: 'POST', body: JSON.stringify({ subject, description, category })
    });
  }

  aiPredictSLA(data) {
    return this._request('/api/ai/predict-sla', {
      method: 'POST', body: JSON.stringify(data)
    });
  }

  aiInsights() { return this._request('/api/ai/insights'); }

  // ── Health ───────────────────────────────────────────
  health() { return this._request('/health'); }
}

// Global singleton
const api = new APIClient();
