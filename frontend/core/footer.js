export function render() {
  return `
    <nav class="bottom-nav">
      <button class="nav-item active" data-tab="home" id="footerHome">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        <span>Home</span>
      </button>

      <div class="nav-camera-wrap">
        <button class="nav-camera nav-camera-btn" aria-label="Scan items">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
        </button>
        <span class="nav-camera-label">Scan</span>
      </div>

      <button class="nav-item" data-tab="items" id="footerItems" style="position:relative;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
        <div class="nav-badge" id="itemsBadge">0</div>
        <span>Items</span>
      </button>

      <button class="nav-item" data-tab="profile" id="footerProfile">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
        <span>Profile</span>
      </button>
    </nav>
  `;
}

export function setActiveTab(tab) {
  document.querySelectorAll('.bottom-nav .nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
}

export function updateItemsBadge(count) {
  const badge = document.getElementById('itemsBadge');
  if (badge) badge.textContent = count;
}
