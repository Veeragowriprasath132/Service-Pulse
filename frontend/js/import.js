/**
 * import.js — Import tickets from Excel/CSV/PDF
 * ServicePulse Import Feature
 */

const IMPORT_BACKEND = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://service-pulse-xzsh.onrender.com';

let spSelectedFile = null;

// ── Modal ─────────────────────────────────────────────────
function openImportModal() {
  const modal = document.getElementById('importModal');
  if (modal) {
    modal.style.display = 'flex';
    spClearFile();
    document.getElementById('spImportResult').style.display = 'none';
  }
}

function closeImportModal() {
  const modal = document.getElementById('importModal');
  if (modal) modal.style.display = 'none';
}

// ── File handling ─────────────────────────────────────────
function spHandleDrop(e) {
  e.preventDefault();
  const zone = document.getElementById('spDropZone');
  zone.style.borderColor = 'var(--border)';
  zone.style.background  = 'var(--bg-secondary)';
  const file = e.dataTransfer.files[0];
  if (file) spHandleFile(file);
}

function spHandleFile(file) {
  if (!file) return;
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!['.xlsx','.xls','.csv','.pdf'].includes(ext)) {
    alert('Unsupported file. Please use Excel (.xlsx), CSV (.csv), or PDF (.pdf)');
    return;
  }
  spSelectedFile = file;

  // Show file info
  document.getElementById('spFileInfo').style.display = 'flex';
  document.getElementById('spFileName').textContent   = file.name;
  document.getElementById('spFileSize').textContent   = (file.size / 1024).toFixed(1) + ' KB · ' + ext.toUpperCase().replace('.','');

  // Enable import button
  const btn = document.getElementById('spImportBtn');
  btn.disabled = false;
  btn.style.background = 'var(--accent)';
  btn.style.cursor     = 'pointer';

  // Highlight drop zone
  document.getElementById('spDropZone').style.borderColor = 'var(--accent)';
}

function spClearFile() {
  spSelectedFile = null;
  document.getElementById('spFileInfo').style.display = 'none';
  document.getElementById('spImportFile').value        = '';
  const btn = document.getElementById('spImportBtn');
  if (btn) { btn.disabled = true; btn.style.background = '#ccc'; btn.style.cursor = 'not-allowed'; }
  const zone = document.getElementById('spDropZone');
  if (zone) { zone.style.borderColor = 'var(--border)'; zone.style.background = 'var(--bg-secondary)'; }
}

// ── Import ────────────────────────────────────────────────
async function spImportTickets() {
  if (!spSelectedFile) return;

  const btn    = document.getElementById('spImportBtn');
  const result = document.getElementById('spImportResult');

  btn.disabled   = true;
  btn.innerHTML  = '<div style="width:14px;height:14px;border:2px solid rgba(255,255,255,0.3);border-top-color:#fff;border-radius:50%;animation:spin 0.7s linear infinite;display:inline-block"></div> Importing...';
  result.style.display = 'none';

  try {
    const formData = new FormData();
    formData.append('file', spSelectedFile);

    const res  = await fetch(`${IMPORT_BACKEND}/api/import/tickets`, {
      method:  'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('sp-token')}` },
      body:    formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Import failed');

    result.style.display = 'block';
    result.innerHTML = `
      <div style="background:#E3FCEF;border:1px solid #ABF5D1;border-radius:10px;padding:16px">
        <div style="font-size:15px;font-weight:600;color:#00875A;margin-bottom:12px">
          ✅ Import Successful!
        </div>
        <div style="display:flex;gap:14px;margin-bottom:12px">
          <div style="text-align:center;padding:10px 16px;background:#fff;border-radius:8px;flex:1">
            <div style="font-size:24px;font-weight:700;color:#00875A">${data.created_count}</div>
            <div style="font-size:11px;color:#5E6C84">Imported</div>
          </div>
          <div style="text-align:center;padding:10px 16px;background:#fff;border-radius:8px;flex:1">
            <div style="font-size:24px;font-weight:700;color:#DE350B">${data.failed_count}</div>
            <div style="font-size:11px;color:#5E6C84">Failed</div>
          </div>
          <div style="text-align:center;padding:10px 16px;background:#fff;border-radius:8px;flex:1">
            <div style="font-size:24px;font-weight:700;color:#0052CC">${data.total_rows}</div>
            <div style="font-size:11px;color:#5E6C84">Total Rows</div>
          </div>
        </div>
        ${data.created?.length ? `
          <div style="font-size:12px;font-weight:600;color:#172B4D;margin-bottom:6px">Created tickets:</div>
          <div style="max-height:140px;overflow-y:auto">
            ${data.created.map(t => `
              <div style="display:flex;align-items:center;gap:8px;padding:5px 8px;background:#fff;border-radius:5px;margin-bottom:3px;font-size:12px">
                <span style="color:#0052CC;font-weight:600;min-width:90px">${t.ticket_number}</span>
                <span style="color:#172B4D;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${t.subject}</span>
                <span style="color:#5E6C84;font-size:10px">${t.priority}</span>
              </div>`).join('')}
          </div>` : ''}
        ${data.failed?.length ? `
          <div style="margin-top:8px;font-size:11px;color:#DE350B">
            ${data.failed.map(f => `⚠️ Row ${f.row}: ${f.reason}`).join('<br>')}
          </div>` : ''}
      </div>`;

    // Refresh dashboard after 2 seconds
    setTimeout(() => {
      closeImportModal();
      if (typeof loadDashboardData === 'function') loadDashboardData();
      if (typeof refreshDashboard   === 'function') refreshDashboard();
      // Try to refresh current page
      const page = window.State?.currentPage || 'dashboard';
      if (typeof nav === 'function') nav(page);
    }, 2500);

  } catch(e) {
    result.style.display = 'block';
    result.innerHTML = `
      <div style="background:#FFEBE6;border:1px solid #FFB3A0;border-radius:8px;padding:12px;font-size:13px;color:#DE350B">
        ❌ Import failed: ${e.message}
      </div>`;
  }

  btn.disabled  = false;
  btn.innerHTML = '<i class="ti ti-file-import"></i> Import Tickets';
  btn.style.background = 'var(--accent)';
}

// ── Download template ─────────────────────────────────────
async function downloadTemplate() {
  try {
    const res = await fetch(`${IMPORT_BACKEND}/api/import/template`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('sp-token')}` }
    });
    if (!res.ok) throw new Error('Failed to download');
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'servicepulse_import_template.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch(e) {
    alert('Template download failed: ' + e.message);
  }
}

// Close modal on overlay click
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('importModal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeImportModal();
    });
  }
});
