/**
 * auth-guard.js — Authentication guard for ServicePulse
 * Add this as the FIRST script in index.html
 */

const BACKEND_URL = 'https://service-pulse-xzsh.onrender.com';

// ── Auth State ────────────────────────────────────────────
const Auth = {
  token: localStorage.getItem('sp-token'),
  user:  JSON.parse(localStorage.getItem('sp-user') || 'null'),

  isLoggedIn() { return !!this.token && !!this.user; },

  hasPermission(page) {
    if (!this.user) return false;
    return this.user.permissions?.includes(page) || this.user.role === 'superadmin';
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
    window.location.href = 'login.html';
  }
};

// ── Guard — redirect to login if not authenticated ────────
(function() {
  if (!Auth.isLoggedIn()) {
    window.location.href = 'login.html';
    return;
  }

  // Inject user info into topbar after DOM loads
  document.addEventListener('DOMContentLoaded', () => {
    injectUserUI();
    setupLogout();
  });
})();

// ── Inject user info into topbar ──────────────────────────
function injectUserUI() {
  const user = Auth.user;
  if (!user) return;

  // Update avatar button
  const avatarBtn = document.querySelector('.avatar-btn');
  if (avatarBtn) {
    avatarBtn.textContent = user.avatar || user.username.slice(0,2).toUpperCase();
    avatarBtn.title = `${user.full_name} (${user.role})`;
  }

  // Add user dropdown after avatar
  const topbarRight = document.querySelector('.topbar-right') || document.querySelector('.navbar-right');
  if (topbarRight && !document.getElementById('userDropdown')) {
    const userInfo = document.createElement('div');
    userInfo.id = 'userDropdown';
    userInfo.style.cssText = 'position:relative;display:inline-flex;align-items:center;gap:8px;cursor:pointer;';
    userInfo.innerHTML = `
      <div style="display:flex;flex-direction:column;text-align:right">
        <span style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.9)">${user.full_name}</span>
        <span style="font-size:10px;color:rgba(255,255,255,0.55);text-transform:capitalize">${user.role}</span>
      </div>
    `;
    topbarRight.appendChild(userInfo);
  }

  // Hide restricted nav items based on role
  hideRestrictedItems(user);
}

function hideRestrictedItems(user) {
  // Hide admin-only items for non-admins
  if (user.role === 'viewer') {
    const createBtns = document.querySelectorAll('[data-page="create"], [onclick*="create"]');
    createBtns.forEach(btn => {
      if (btn.textContent.includes('Create')) btn.style.display = 'none';
    });
  }
}

// ── Setup logout button ───────────────────────────────────
function setupLogout() {
  // Find theme button in sidebar footer and add logout after it
  const sidebarFooter = document.querySelector('.sidebar-footer') || document.querySelector('.sidebar-bottom');
  if (sidebarFooter && !document.getElementById('logoutBtn')) {
    const logoutBtn = document.createElement('button');
    logoutBtn.id = 'logoutBtn';
    logoutBtn.className = 'nav-item';
    logoutBtn.innerHTML = '<i class="ti ti-logout icon" style="color:#A32D2D"></i><span style="color:#A32D2D">Sign Out</span>';
    logoutBtn.onclick = () => {
      if (confirm(`Sign out, ${Auth.user?.full_name}?`)) Auth.logout();
    };
    sidebarFooter.appendChild(logoutBtn);
  }
}

// ── Override fetch to add auth headers ────────────────────
const _originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
  const urlStr = typeof url === 'string' ? url : url.toString();
  
  // Only add auth headers for ServicePulse backend
  // Never intercept Groq, Anthropic, or external APIs
  if (urlStr.includes(BACKEND_URL) && 
      !urlStr.includes('groq.com') && 
      !urlStr.includes('anthropic.com') &&
      !urlStr.includes('api.anthropic') &&
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
  // Add auth header ONLY for ServicePulse backend calls
  if (typeof url === 'string' && 
      url.includes(BACKEND_URL) && 
      !url.includes('anthropic.com') && 
      !url.includes('groq.com')) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${Auth.token}`
    };
  }
return _originalFetch(url, options).then(res => {
    // Auto-logout on 401
    if (res.status === 401 && url.includes(BACKEND_URL)) {
      Auth.logout();
    }
    return res;
  });
