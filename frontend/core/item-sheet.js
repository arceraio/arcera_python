const API = 'http://localhost:5000';

let onRefresh = null;
let currentItem = null;

/* ── Fullscreen zoom state ── */
let fsScale = 1;
let fsTx = 0;
let fsTy = 0;
let fsDragging = false;
let fsDragLast = { x: 0, y: 0 };
let fsPinchInitDist = 0;
let fsPinchInitScale = 1;

export function init(refreshCb) {
  onRefresh = refreshCb;

  document.body.insertAdjacentHTML('beforeend', `
    <div class="item-sheet-overlay" id="itemSheetOverlay"></div>
    <div class="item-sheet" id="itemSheet">
      <div class="item-sheet-handle"></div>
      <div id="itemSheetContent"></div>
    </div>

    <div class="photo-fullscreen" id="photoFullscreen">
      <button class="photo-fs-close" id="photoFsClose" aria-label="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <span class="photo-fs-hint" id="photoFsHint"></span>
      <div class="photo-zoom-wrap" id="photoZoomWrap">
        <img class="photo-fs-img" id="photoFsImg" alt="">
        <div class="photo-yolo-box" id="photoYoloBox"></div>
      </div>
    </div>
  `);

  document.getElementById('itemSheetOverlay').addEventListener('click', closeSheet);
  document.getElementById('photoFsClose').addEventListener('click', closeFullscreen);

  const fs = document.getElementById('photoFullscreen');

  /* desktop: scroll to zoom */
  fs.addEventListener('wheel', e => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    fsScale = Math.max(1, Math.min(6, fsScale * factor));
    if (fsScale === 1) { fsTx = 0; fsTy = 0; }
    applyTransform();
  }, { passive: false });

  /* desktop: drag to pan */
  fs.addEventListener('mousedown', e => {
    if (fsScale <= 1) return;
    fsDragging = true;
    fsDragLast = { x: e.clientX, y: e.clientY };
    fs.style.cursor = 'grabbing';
  });
  window.addEventListener('mousemove', e => {
    if (!fsDragging) return;
    fsTx += e.clientX - fsDragLast.x;
    fsTy += e.clientY - fsDragLast.y;
    fsDragLast = { x: e.clientX, y: e.clientY };
    applyTransform();
  });
  window.addEventListener('mouseup', () => {
    fsDragging = false;
    fs.style.cursor = '';
  });

  /* mobile: pinch to zoom + single-finger pan */
  fs.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      fsPinchInitDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      fsPinchInitScale = fsScale;
    } else if (e.touches.length === 1 && fsScale > 1) {
      fsDragging = true;
      fsDragLast = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }, { passive: true });

  fs.addEventListener('touchmove', e => {
    e.preventDefault();
    if (e.touches.length === 2) {
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      fsScale = Math.max(1, Math.min(6, fsPinchInitScale * (dist / fsPinchInitDist)));
      if (fsScale === 1) { fsTx = 0; fsTy = 0; }
      applyTransform();
    } else if (e.touches.length === 1 && fsDragging) {
      fsTx += e.touches[0].clientX - fsDragLast.x;
      fsTy += e.touches[0].clientY - fsDragLast.y;
      fsDragLast = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      applyTransform();
    }
  }, { passive: false });

  fs.addEventListener('touchend', e => {
    if (e.touches.length < 2) fsDragging = false;
  }, { passive: true });

  /* keyboard: Escape to close */
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeFullscreen();
  });

  /* reposition bbox on resize */
  window.addEventListener('resize', () => {
    const img = document.getElementById('photoFsImg');
    if (img.complete && currentItem) positionBbox(currentItem.bbox, img);
  });
}

export function open(item) {
  currentItem = item;
  renderSheet();
  document.getElementById('itemSheetOverlay').classList.add('open');
  document.getElementById('itemSheet').classList.add('open');
}

function closeSheet() {
  document.getElementById('itemSheetOverlay').classList.remove('open');
  document.getElementById('itemSheet').classList.remove('open');
}

/* ── Fullscreen ── */

function openFullscreen(item) {
  fsScale = 1; fsTx = 0; fsTy = 0;
  applyTransform();

  const img = document.getElementById('photoFsImg');
  img.src = `${API}/photo/${item.id}`;
  img.onload = () => positionBbox(item.bbox, img);

  const isMobile = 'ontouchstart' in window;
  document.getElementById('photoFsHint').textContent = isMobile
    ? 'Pinch to zoom · drag to pan'
    : 'Scroll to zoom · drag to pan · Esc to close';

  document.getElementById('photoFullscreen').classList.add('open');
}

function closeFullscreen() {
  document.getElementById('photoFullscreen').classList.remove('open');
  document.getElementById('photoFsImg').src = '';
  document.getElementById('photoYoloBox').style.display = 'none';
}

function applyTransform() {
  document.getElementById('photoZoomWrap').style.transform =
    `translate(${fsTx}px, ${fsTy}px) scale(${fsScale})`;
}

function positionBbox(bbox, img) {
  const box = document.getElementById('photoYoloBox');
  if (!bbox) { box.style.display = 'none'; return; }

  const [x1, y1, x2, y2] = bbox;
  const ew = img.offsetWidth;
  const eh = img.offsetHeight;
  const nw = img.naturalWidth;
  const nh = img.naturalHeight;

  /* account for object-fit: contain letterboxing */
  const imgRatio  = nw / nh;
  const elemRatio = ew / eh;
  let rw, rh, rx, ry;
  if (imgRatio > elemRatio) {
    rw = ew; rh = ew / imgRatio; rx = 0; ry = (eh - rh) / 2;
  } else {
    rh = eh; rw = eh * imgRatio; rx = (ew - rw) / 2; ry = 0;
  }

  const sx = rw / nw;
  const sy = rh / nh;

  box.style.display = 'block';
  box.style.left   = `${rx + x1 * sx}px`;
  box.style.top    = `${ry + y1 * sy}px`;
  box.style.width  = `${(x2 - x1) * sx}px`;
  box.style.height = `${(y2 - y1) * sy}px`;
}

/* ── Item detail sheet ── */

function renderSheet() {
  const it = currentItem;

  const hero = it.crop_url
    ? `<img class="item-sheet-hero-img" src="${it.crop_url}" alt="${it.label}">`
    : `<div class="item-sheet-hero-placeholder">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
       </div>`;

  document.getElementById('itemSheetContent').innerHTML = `
    <div class="item-sheet-hero" id="itemSheetHero">
      ${hero}
      <div class="item-sheet-hero-overlay">
        <span class="item-sheet-hero-name">${it.label}</span>
        <span class="item-card-room">${it.room}</span>
      </div>
      <button class="item-sheet-close" id="itemSheetClose" aria-label="Close">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <span class="item-sheet-hero-hint">Double-tap to view full photo</span>
    </div>

    <div class="item-sheet-body">
      <div class="item-sheet-field">
        <label class="item-sheet-label">Name</label>
        <input id="itemSheetName" type="text" class="item-sheet-input"
          value="${it.label}" placeholder="Item name">
      </div>
      <div class="item-sheet-field">
        <label class="item-sheet-label">Description</label>
        <textarea id="itemSheetDesc" class="item-sheet-input item-sheet-textarea"
          placeholder="Add a description…">${it.description || ''}</textarea>
      </div>
      <div class="item-sheet-field">
        <label class="item-sheet-label">Purchase Year</label>
        <input id="itemSheetYear" type="number" class="item-sheet-input"
          value="${it.purchase_year || ''}" placeholder="${new Date().getFullYear()}"
          min="1900" max="2099">
      </div>
      <div class="item-sheet-field">
        <label class="item-sheet-label">Cost ($)</label>
        <input id="itemSheetCost" type="number" class="item-sheet-input"
          value="${it.cost != null ? it.cost : ''}" placeholder="0.00"
          min="0" step="0.01">
      </div>
      <button class="item-sheet-save" id="itemSheetSave">Save Changes</button>
      <button class="item-sheet-delete" id="itemSheetDelete">Delete Item</button>
    </div>
  `;

  document.getElementById('itemSheetClose').addEventListener('click', closeSheet);

  /* double-click/tap hero → fullscreen */
  document.getElementById('itemSheetHero').addEventListener('dblclick', () => openFullscreen(it));

  document.getElementById('itemSheetSave').addEventListener('click', async () => {
    const name        = document.getElementById('itemSheetName').value.trim() || null;
    const description = document.getElementById('itemSheetDesc').value.trim() || null;
    const year        = parseInt(document.getElementById('itemSheetYear').value) || null;
    const cost        = parseFloat(document.getElementById('itemSheetCost').value) || null;
    await fetch(`${API}/items/${it.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, purchase_year: year, cost }),
    });
    closeSheet();
    onRefresh();
  });

  document.getElementById('itemSheetDelete').addEventListener('click', async () => {
    await fetch(`${API}/items/${it.id}`, { method: 'DELETE' });
    closeSheet();
    onRefresh();
  });
}
