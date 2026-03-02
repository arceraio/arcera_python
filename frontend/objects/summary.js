const TOTAL_ROOMS = 8;
const fmtFull = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });

function fmtValue(v) {
  if (v >= 1000000) return `$${(v / 1000000).toFixed(1)}M`;
  if (v >= 10000)   return `$${Math.round(v / 1000)}K`;
  if (v >= 1000)    return `$${(v / 1000).toFixed(1)}K`;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v);
}

function dateLabel(isoString) {
  const now = new Date();
  const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo   = new Date(today.getTime() - 6 * 86400000);
  const d   = new Date(isoString);
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  if (day.getTime() === today.getTime())     return 'Today';
  if (day.getTime() === yesterday.getTime()) return 'Yesterday';
  if (day >= weekAgo)                        return 'This Week';
  return d.toLocaleString('default', { month: 'long', year: 'numeric' });
}

function renderTimeline(items) {
  const groups = new Map();
  [...items]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .forEach(it => {
      const label = dateLabel(it.created_at);
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(it);
    });

  return [...groups.entries()].map(([label, group]) => {
    const limit = 15;
    const visible = group.slice(0, limit);
    const remaining = group.length - visible.length;
    return `
      <div class="timeline-section">
        <h3 class="timeline-label">${label}</h3>
        <div class="items-grid">
          ${visible.map(it => `
            <div class="item-card" data-id="${it.id}">
              ${it.crop_url
                ? `<img class="item-card-thumb" src="${it.crop_url}" alt="${it.label}" loading="lazy">`
                : `<div class="item-card-thumb item-card-thumb-placeholder">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
                      <polyline points="21 15 16 10 5 21"/>
                    </svg>
                   </div>`}
              <div class="item-card-name">${it.label}</div>
              <div class="item-card-cost">${it.cost != null ? fmtFull.format(it.cost) : '—'}</div>
              <span class="item-card-room">${it.room}</span>
            </div>
          `).join('')}
        </div>
        ${remaining > 0 ? `
          <button class="timeline-see-more" data-navigate="items">
            +${remaining} more item${remaining !== 1 ? 's' : ''} — View all
          </button>` : ''}
      </div>
    `;
  }).join('');
}

export function render(items) {
  const total = items.length;

  if (total === 0) {
    return `
      <div class="hero-banner">
        <svg class="hero-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <h2 class="hero-title">Start Documenting Your Belongings</h2>
        <p class="hero-subtitle">Scan a room with your camera to begin building your inventory.</p>
      </div>
    `;
  }

  const totalValue  = items.reduce((sum, it) => sum + (it.cost || 0), 0);
  const valued      = items.filter(it => it.cost != null).length;
  const duplicates  = items.filter(it => it.duplicate_of != null).length;
  const rooms       = new Set(items.map(it => it.room_id).filter(Boolean)).size;

  const roomPct    = Math.round((rooms      / TOTAL_ROOMS) * 100);
  const valuedPct  = Math.round((valued     / total)       * 100);
  const dupPct     = Math.round((duplicates / total)       * 100);

  return `
    <div class="summary-stats">

      <div class="summary-stat" style="
        --stat-color: var(--blue-500);
        --stat-bg: #EFF6FF;
        --stat-border: #BFDBFE;
      ">
        <div class="summary-stat-body">
          <span class="summary-stat-label">Total Items</span>
          <span class="summary-stat-value">${total}</span>
          <span class="summary-stat-sub">${rooms} of ${TOTAL_ROOMS} rooms</span>
        </div>
        <div class="summary-stat-bar-track">
          <div class="summary-stat-bar-fill" style="width: ${roomPct}%"></div>
        </div>
      </div>

      <div class="summary-stat summary-stat--link"
           data-navigate="items" data-filter="needsinfo"
           style="
             --stat-color: var(--emerald);
             --stat-bg: #ECFDF5;
             --stat-border: #A7F3D0;
           ">
        <div class="summary-stat-body">
          <span class="summary-stat-label">Total Value</span>
          <span class="summary-stat-value summary-stat-value--currency">${fmtValue(totalValue)}</span>
          <span class="summary-stat-sub">${valued} / ${total} valued</span>
        </div>
        <div class="summary-stat-bar-track">
          <div class="summary-stat-bar-fill" style="width: ${valuedPct}%"></div>
        </div>
      </div>

      <div class="summary-stat${duplicates > 0 ? ' summary-stat--link' : ''}"
           ${duplicates > 0 ? 'data-navigate="items" data-filter="duplicates"' : ''}
           style="
             --stat-color: var(--amber);
             --stat-bg: #FFFBEB;
             --stat-border: #FDE68A;
           ">
        <div class="summary-stat-body">
          <span class="summary-stat-label">Duplicates</span>
          <span class="summary-stat-value${duplicates > 0 ? ' summary-stat-value--warn' : ''}">${duplicates}</span>
          <span class="summary-stat-sub">${duplicates > 0 ? `${dupPct}% of items` : 'None found'}</span>
        </div>
        <div class="summary-stat-bar-track">
          <div class="summary-stat-bar-fill" style="width: ${dupPct}%"></div>
        </div>
      </div>

    </div>
    ${renderTimeline(items)}
  `;
}
