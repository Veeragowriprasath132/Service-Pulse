/**
 * auth-guard.js — Complete Authentication & Access Control
 * ServicePulse Leadership Dashboard
 * 
 * Roles:
 *   superadmin → full access to everything
 *   manager    → dashboard, sla, workload, teams, tickets, create, connectors, ai, export
 *   teamlead   → dashboard, sla, workload, teams, tickets, create, ai
 *   viewer     → dashboard, sla, workload, teams (read-only, no create/export/connectors)
 */

const BACKEND_URL = 'https://service-pulse-xzsh.onrender.com';

// ── Role Permission Map ───────────────────────────────────
const ROLE_PERMISSIONS = {
  superadmin: {
    pages:      ['dashboard','sla','workload','teams','tickets','create','connectors','ai'],
    canCreate:  true,
    canExport:  true,
    canConnect: true,
    canAdmin:   true,
    label:      'Super Admin',
    color:      '#0C447C'
  },
  manager: {
    pages:      ['dashboard','sla','workload','teams','tickets','create','connectors','ai'],
    canCreate:  true,
    canExport:  true,
    canConnect: true,
    canAdmin:   false,
    label:      'Manager',
    color:      '#185FA5'
  },
  teamlead: {
    pages:      ['dashboard','sla','workload','teams','tickets','create','ai'],
    canCreate:  true,
    canExport:  false,
    canConnect: false,
    canAdmin:   false,
    label:      'Team Lead',
    color:      '#BA7517'
  },
  viewer: {
    pages:      ['dashboard','sla','workload','teams','tickets'],
    canCreate:  false,
    canExport:  false,
    canConnect: false,
    canAdmin:   false,
    label:      'Viewer',
    color:      '#0F6E56'
  }
};

// ── Auth State ────────────────────────────────────────────
const Auth = {
  token: localStorage.getItem('sp-token'),
  user:  JSON.parse(localStorage.getItem('sp-user') || 'null'),

  isLoggedIn() {
    return !!this.token && !!this.user;
  },

  getRole() {
    return this.user?.role || 'viewer';
  },

  getPermissions() {
    return ROLE_PERMISSIONS[this.getRole()] || ROLE_PERMISSIONS.viewer;
  },

  canAccess(page) {
    const perms = this.getPermissions();
    return perms.pages.includes(page);
  },

  canCreate() {
    return this.getPermissions().canCreate;
  },

  canExport() {
    return this.getPermissions().canExport;
  },

  canConnect() {
    return this.getPermissions().canConnect;
  },

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };
  },

  logout() {
    localStorage.removeItem('sp-token');
    localStorage.removeItem('sp-user');
    const base = window.location.hostname === 'localhost' ? '' : '/Service-Pulse';
    window.location.href = `${base}/login.html`;
  }
};

// ── Guard — redirect to login if not authenticated ────────
(function() {
  if (!Auth.isLoggedIn()) {
    const base = window.location.hostname === 'localhost' ? '' : '/Service-Pulse';
    window.location.href = `${base}/login.html`;
    return;
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupUserUI();
    applyAccessRestrictions();
    setupLogout();
    showWelcomeBanner();
  });
})();

// ── Setup User UI in topbar ───────────────────────────────
function setupUserUI() {
  const user  = Auth.user;
  const perms = Auth.getPermissions();
  if (!user) return;

  // Update avatar
  const avatarBtn = document.querySelector('.avatar-btn');
  if (avatarBtn) {
    avatarBtn.textContent = user.avatar || user.username.slice(0,2).toUpperCase();
    avatarBtn.title = `${user.full_name} (${perms.label})`;
    avatarBtn.style.background = perms.color;
  }

  // Add user info chip in topbar
  const topbarActions = document.querySelector('.topbar-actions') || document.querySelector('.topbar-right');
  if (topbarActions && !document.getElementById('userChip')) {
    const chip = document.createElement('div');
    chip.id = 'userChip';
    chip.style.cssText = `
      display:flex; align-items:center; gap:8px;
      background:${perms.color}18; border:1px solid ${perms.color}40;
      border-radius:20px; padding:4px 12px 4px 4px; cursor:pointer;
    `;
    chip.innerHTML = `
      <div style="width:26px;height:26px;border-radius:50%;background:${perms.color};
        color:#fff;display:flex;align-items:center;justify-content:center;
        font-size:11px;font-weight:700">${user.avatar || user.username.slice(0,2).toUpperCase()}</div>
      <div>
        <div style="font-size:12px;font-weight:600;color:var(--text-primary)">${user.full_name}</div>
        <div style="font-size:10px;color:${perms.color};font-weight:600">${perms.label}</div>
      </div>
    `;
    chip.onclick = () => {
      if (confirm(`Sign out as ${user.full_name}?`)) Auth.logout();
    };

    // Insert before the Ask AI button
    const askAiBtn = topbarActions.querySelector('.topbar-btn.primary') ||
                     topbarActions.lastElementChild;
    if (askAiBtn) {
      topbarActions.insertBefore(chip, askAiBtn);
    } else {
      topbarActions.appendChild(chip);
    }
  }
}

// ── Apply Access Restrictions ─────────────────────────────
function applyAccessRestrictions() {
  const perms = Auth.getPermissions();

  // Hide nav items based on role
  document.querySelectorAll('.nav-item[data-page]').forEach(item => {
    const page = item.getAttribute('data-page');
    if (page && !perms.pages.includes(page)) {
      item.style.display = 'none';
    }
  });

  // Hide Create Ticket button/nav for viewers
  if (!perms.canCreate) {
    document.querySelectorAll('[data-page="create"], [onclick*="create"]').forEach(el => {
      if (el.textContent.toLowerCase().includes('create') ||
          el.textContent.toLowerCase().includes('ticket')) {
        el.style.display = 'none';
      }
    });
    // Hide topbar create button
    document.querySelectorAll('.topbar-btn').forEach(btn => {
      if (btn.textContent.includes('Create') || btn.textContent.includes('New')) {
        btn.style.display = 'none';
      }
    });
  }

  // Hide Export buttons for non-exporters
  if (!perms.canExport) {
    document.querySelectorAll('.export-btn, [onclick*="exportCSV"], [onclick*="exportPDF"]').forEach(el => {
      el.style.display = 'none';
    });
  }

  // Hide Connectors for non-permitted roles
  if (!perms.canConnect) {
    document.querySelectorAll('[data-page="connectors"]').forEach(el => {
      el.style.display = 'none';
    });
  }

  // Override nav function to check permissions
  const originalNav = window.nav;
  if (originalNav) {
    window.nav = function(page, el) {
      if (page !== 'dashboard' && !Auth.canAccess(page)) {
        showAccessDenied(page);
        return;
      }
      originalNav(page, el);
    };
  }
}

// ── Access Denied Message ─────────────────────────────────
function showAccessDenied(page) {
  const perms = Auth.getPermissions();
  const existing = document.getElementById('accessDeniedMsg');
  if (existing) existing.remove();

  const msg = document.createElement('div');
  msg.id = 'accessDeniedMsg';
  msg.style.cssText = `
    position:fixed; top:70px; left:50%; transform:translateX(-50%);
    background:#FCEBEB; border:1px solid #F5B7B7; border-radius:10px;
    padding:14px 24px; font-size:13px; color:#A32D2D; z-index:999;
    display:flex; align-items:center; gap:10px; box-shadow:0 4px 12px rgba(0,0,0,0.1);
  `;
  msg.innerHTML = `
    <i class="ti ti-lock" style="font-size:18px"></i>
    <div>
      <strong>Access Restricted</strong> — Your role (${perms.label}) doesn't have
      permission to access <strong>${page}</strong>.
      Contact your administrator for access.
    </div>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;
      cursor:pointer;color:#A32D2D;font-size:18px;margin-left:8px">×</button>
  `;
  document.body.appendChild(msg);
  setTimeout(() => msg.remove(), 4000);
}

// ── Welcome Banner ────────────────────────────────────────
function showWelcomeBanner() {
  const user  = Auth.user;
  const perms = Auth.getPermissions();
  if (!user || sessionStorage.getItem('sp-welcomed')) return;
  sessionStorage.setItem('sp-welcomed', '1');

  const banner = document.createElement('div');
  banner.style.cssText = `
    position:fixed; top:70px; right:20px;
    background:#fff; border:1px solid #DFE1E6; border-radius:10px;
    padding:14px 18px; font-size:13px; z-index:999;
    box-shadow:0 4px 16px rgba(0,0,0,0.12); max-width:280px;
    border-left:4px solid ${perms.color};
  `;
  banner.innerHTML = `
    <div style="font-weight:600;color:var(--text-primary);margin-bottom:4px">
      Welcome, ${user.full_name}! 👋
    </div>
    <div style="color:#5a6070;font-size:12px">
      Signed in as <strong style="color:${perms.color}">${perms.label}</strong>
    </div>
    <div style="color:#8892a4;font-size:11px;margin-top:4px">
      Access: ${perms.pages.join(', ')}
    </div>
  `;
  document.body.appendChild(banner);
  setTimeout(() => {
    banner.style.transition = 'opacity 0.5s';
    banner.style.opacity = '0';
    setTimeout(() => banner.remove(), 500);
  }, 3500);
}

// ── Logout Button ─────────────────────────────────────────
function setupLogout() {
  const sidebarFooter = document.querySelector('.sidebar-footer') ||
                        document.querySelector('.sidebar-bottom');
  if (sidebarFooter && !document.getElementById('logoutBtn')) {
    const logoutBtn = document.createElement('button');
    logoutBtn.id = 'logoutBtn';
    logoutBtn.className = 'nav-item';
    logoutBtn.style.cssText = 'color:#A32D2D;margin-top:4px';
    logoutBtn.innerHTML = `
      <i class="ti ti-logout icon" style="color:#A32D2D"></i>
      <span style="color:#A32D2D">Sign Out</span>
    `;
    logoutBtn.onclick = () => {
      if (confirm(`Sign out as ${Auth.user?.full_name}?`)) Auth.logout();
    };
    sidebarFooter.appendChild(logoutBtn);
  }
}

// ── Fetch Override — add auth headers for backend calls ───
const _originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
  const urlStr = typeof url === 'string' ? url : url.toString();

  // Only add auth headers for ServicePulse backend API calls
  if (urlStr.includes(BACKEND_URL) &&
      !urlStr.includes('groq.com') &&
      !urlStr.includes('anthropic.com') &&
      urlStr.includes('/api/')) {
    options = { ...options };
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${Auth.token}`
    };
  }

  return _originalFetch(url, options).then(res => {
    if (res.status === 401 && urlStr.includes(BACKEND_URL)) {
      Auth.logout();
    }
    return res;
  });
};
