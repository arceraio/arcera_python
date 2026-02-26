export function render(items) {
  const total = items.length;
  const value = items.reduce((sum, it) => sum + (it.cost || 0), 0);
  const rooms = new Set(items.map(it => it.room_id).filter(Boolean)).size;
  const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 });

  const hasItems = total > 0;
  const title = hasItems
    ? 'Your Belongings Are Protected'
    : 'Start Documenting Your Belongings';
  const subtitle = hasItems
    ? `${total} item${total !== 1 ? 's' : ''} across ${rooms} room${rooms !== 1 ? 's' : ''} \u2014 valued at ${fmt.format(value)}`
    : 'Scan a room with your camera to begin building your inventory.';

  return `
    <div class="hero-banner">
      <svg class="hero-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
      <h2 class="hero-title">${title}</h2>
      <p class="hero-subtitle">${subtitle}</p>
    </div>
  `;
}
