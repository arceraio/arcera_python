const ROOMS = [
  "Living Room", "Bedroom", "Kitchen", "Bathroom",
  "Dining Room", "Office", "Garage", "Other",
];

export function render(items, activeFilter = 0) {
  const filtered = activeFilter === 0
    ? items
    : activeFilter === 'duplicates'
      ? items.filter(it => it.duplicate_of != null)
      : activeFilter === 'needsinfo'
        ? items.filter(it => it.cost == null || it.purchase_year == null)
        : items.filter(it => it.room_id === activeFilter);

  const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });

  if (items.length === 0) {
    return `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
        <p>Start by scanning a room</p>
        <span>Use the Camera to document your belongings. We\u2019ll keep them safe.</span>
      </div>
    `;
  }

  const roomCounts = {};
  items.forEach(it => {
    const rid = it.room_id;
    if (rid && rid >= 1 && rid <= ROOMS.length) {
      roomCounts[rid] = (roomCounts[rid] || 0) + 1;
    }
  });

  const duplicateCount = items.filter(it => it.duplicate_of != null).length;
  const needsInfoCount = items.filter(it => it.cost == null || it.purchase_year == null).length;

  const chips = [`<button class="room-chip${activeFilter === 0 ? ' active' : ''}" data-room="0">All (${items.length})</button>`];
  if (duplicateCount > 0) {
    chips.push(`<button class="room-chip room-chip--warning${activeFilter === 'duplicates' ? ' active' : ''}" data-room="duplicates">Duplicates (${duplicateCount})</button>`);
  }
  if (needsInfoCount > 0) {
    chips.push(`<button class="room-chip room-chip--info${activeFilter === 'needsinfo' ? ' active' : ''}" data-room="needsinfo">Needs Info (${needsInfoCount})</button>`);
  }
  Object.keys(roomCounts)
    .sort((a, b) => roomCounts[b] - roomCounts[a])
    .forEach(rid => {
      const id = parseInt(rid);
      const name = ROOMS[id - 1];
      chips.push(`<button class="room-chip${activeFilter === id ? ' active' : ''}" data-room="${id}">${name} (${roomCounts[id]})</button>`);
    });

  const cards = filtered.map(it => {
    const missingInfo = it.cost == null || it.purchase_year == null;
    return `
    <div class="item-card" data-id="${it.id}">
      <button class="item-card-delete" data-id="${it.id}" aria-label="Remove item">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      ${it.crop_url
        ? `<img class="item-card-thumb" src="${it.crop_url}" alt="${it.label}" loading="lazy" />`
        : `<div class="item-card-thumb item-card-thumb-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
           </div>`
      }
      <div class="item-card-name">${it.label}</div>
      <div class="item-card-cost">${it.cost != null ? fmt.format(it.cost) : '\u2014'}</div>
      <span class="item-card-room">${it.room}</span>
      ${it.duplicate_of != null ? `<span class="item-card-duplicate">Duplicate of #${it.duplicate_of}</span>` : ''}
      ${missingInfo ? `<span class="item-card-needs-info">Needs Info</span>` : ''}
      <div class="item-card-year">${it.purchase_year || ''}</div>
    </div>
  `}).join('');

  return `
    <div class="room-chips">${chips.join('')}</div>
    <div class="items-grid">${cards}</div>
  `;
}
