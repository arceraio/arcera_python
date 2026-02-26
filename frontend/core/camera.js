const ROOMS = [
  "Living Room", "Bedroom", "Kitchen", "Bathroom",
  "Dining Room", "Office", "Garage", "Other",
];

const API = 'http://localhost:5000';

let onRefresh = null;
let currentFile = null;

export function init(refreshCb) {
  onRefresh = refreshCb;

  document.body.insertAdjacentHTML('beforeend', `
    <div class="camera-overlay" id="cameraOverlay"></div>
    <div class="camera-sheet" id="cameraSheet">
      <div class="camera-sheet-handle"></div>
      <div class="camera-sheet-header">
        <span class="camera-sheet-title">Scan Items</span>
        <button class="camera-sheet-close" id="cameraClose">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="camera-body" id="cameraBody"></div>
    </div>
  `);

  document.querySelector('.nav-camera-btn').addEventListener('click', openModal);
  document.getElementById('cameraOverlay').addEventListener('click', closeModal);
  document.getElementById('cameraClose').addEventListener('click', closeModal);
}

export { openModal as open };

function openModal() {
  currentFile = null;
  document.getElementById('cameraOverlay').classList.add('open');
  document.getElementById('cameraSheet').classList.add('open');
  showPickScreen();
}

function closeModal() {
  document.getElementById('cameraOverlay').classList.remove('open');
  document.getElementById('cameraSheet').classList.remove('open');
}

function setBody(html) {
  document.getElementById('cameraBody').innerHTML = html;
}

/* ── Step 1: Pick ── */

function showPickScreen() {
  setBody(`
    <label class="camera-pick-area" for="cameraFileInput">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
        <circle cx="12" cy="13" r="4"/>
      </svg>
      <span id="cameraPickLabel">Tap to select a photo</span>
      <span class="camera-pick-sub">JPG, PNG, WEBP</span>
      <input type="file" id="cameraFileInput" accept="image/*" style="display:none">
    </label>
    <button class="camera-action-btn" id="cameraScanBtn" disabled>Scan for Items</button>
  `);

  document.getElementById('cameraFileInput').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    currentFile = file;
    document.getElementById('cameraPickLabel').textContent = file.name;
    document.getElementById('cameraScanBtn').disabled = false;
  });

  document.getElementById('cameraScanBtn').addEventListener('click', doScan);
}

/* ── Step 2: Upload + Detect ── */

async function doScan() {
  if (!currentFile) return;

  setBody(`
    <div class="camera-scanning">
      <div class="camera-spinner"></div>
      <p>Scanning your photo…</p>
    </div>
  `);

  const form = new FormData();
  form.append('image', currentFile);

  let detections = [];

  try {
    await fetch(`${API}/upload`, { method: 'POST', body: form });
    const res = await fetch(`${API}/detect`, { method: 'POST' });
    const data = await res.json();
    detections = data.detections || [];
  } catch {
    setBody(`
      <div class="camera-scanning">
        <p class="camera-error">Could not reach the server. Is it running?</p>
        <button class="camera-action-btn" id="cameraRetryBtn" style="margin-top:16px">Try Again</button>
      </div>
    `);
    document.getElementById('cameraRetryBtn').addEventListener('click', showPickScreen);
    return;
  }

  showReviewScreen(detections);
}

/* ── Step 3: Review detections ── */

function showReviewScreen(detections) {
  if (detections.length === 0) {
    setBody(`
      <div class="camera-scanning">
        <p class="camera-noresult-title">No items detected</p>
        <p class="camera-error">Try a clearer photo with visible objects in frame.</p>
        <button class="camera-action-btn" id="cameraRetryBtn" style="margin-top:16px">Try Again</button>
      </div>
    `);
    document.getElementById('cameraRetryBtn').addEventListener('click', showPickScreen);
    return;
  }

  const roomOptions = ROOMS.map((r, i) =>
    `<option value="${i + 1}">${r}</option>`
  ).join('');

  const rows = detections.map(d => `
    <div class="camera-item-row" data-class-id="${d.class_id}">
      <div class="camera-item-header">
        <div>
          <span class="camera-item-name">${d.label}</span>
          <span class="camera-item-conf">${Math.round(d.confidence * 100)}% match</span>
        </div>
        <button class="camera-item-remove" aria-label="Remove item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="camera-item-fields">
        <div class="camera-field">
          <label>Year</label>
          <input type="number" class="camera-input" name="year"
            placeholder="${new Date().getFullYear()}" min="1900" max="2099">
        </div>
        <div class="camera-field">
          <label>Cost ($)</label>
          <input type="number" class="camera-input" name="cost"
            placeholder="0.00" min="0" step="0.01">
        </div>
        <div class="camera-field camera-field-room">
          <label>Room</label>
          <select class="camera-select" name="room">${roomOptions}</select>
        </div>
      </div>
    </div>
  `).join('');

  setBody(`
    <div class="camera-review-list">${rows}</div>
    <button class="camera-action-btn" id="cameraStoreBtn">
      Add ${detections.length} Item${detections.length !== 1 ? 's' : ''} to Inventory
    </button>
  `);

  document.querySelectorAll('.camera-item-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.camera-item-row').remove();
      const count = document.querySelectorAll('.camera-item-row').length;
      const storeBtn = document.getElementById('cameraStoreBtn');
      if (count === 0) {
        storeBtn.textContent = 'No Items Selected';
        storeBtn.disabled = true;
      } else {
        storeBtn.textContent = `Add ${count} Item${count !== 1 ? 's' : ''} to Inventory`;
      }
    });
  });

  document.getElementById('cameraStoreBtn').addEventListener('click', doStore);
}

/* ── Step 4: Store ── */

async function doStore() {
  const rows = document.querySelectorAll('.camera-item-row');
  if (rows.length === 0) { closeModal(); return; }

  const items = Array.from(rows).map(row => ({
    class_id: parseInt(row.dataset.classId),
    purchase_year: parseInt(row.querySelector('[name="year"]').value) || null,
    cost: parseFloat(row.querySelector('[name="cost"]').value) || null,
    room_id: parseInt(row.querySelector('[name="room"]').value),
  }));

  setBody(`
    <div class="camera-scanning">
      <div class="camera-spinner"></div>
      <p>Saving items…</p>
    </div>
  `);

  try {
    await fetch(`${API}/store`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    });
  } catch {
    // server-side path is still set from upload; close anyway
  }

  closeModal();
  onRefresh();
}
