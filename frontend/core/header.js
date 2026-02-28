export function render() {
  return `
    <header class="header">
      <div class="header-left">
        <button class="hamburger-btn" id="hamburgerBtn" aria-label="Open menu">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <div class="logo">
          <svg viewBox="0 0 40 40" fill="none">
            <path d="M20 4L34 32H6L20 4Z" fill="url(#logoGrad)" opacity="0.85"/>
            <path d="M10 28Q20 18 30 28" stroke="#fff" stroke-width="2.5" fill="none" stroke-linecap="round"/>
            <defs>
              <linearGradient id="logoGrad" x1="6" y1="32" x2="34" y2="4">
                <stop offset="0%" stop-color="#3B82F6"/>
                <stop offset="100%" stop-color="#7DD3FC"/>
              </linearGradient>
            </defs>
          </svg>
          <span class="logo-text">ARCERA</span>
        </div>
      </div>
      <div class="header-right">
        <button class="header-btn header-btn-add" id="headerAddBtn" aria-label="Add item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
        <button class="header-btn header-btn-person" id="headerPersonBtn" aria-label="Profile">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        </button>
      </div>
    </header>
  `;
}
