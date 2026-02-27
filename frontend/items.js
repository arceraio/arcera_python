import { render as renderSummary } from './objects/summary.js';
import { render as renderItemsList } from './objects/items-list.js';

const API = 'http://localhost:5000';

let allItems = [];
let roomFilter = 0;
let activeTab = 'home';

function renderMain() {
  const main = document.querySelector('.main-content');
  if (activeTab === 'items') {
    main.innerHTML = renderItemsList(allItems, roomFilter);
    bindMainEvents();
  } else {
    main.innerHTML = renderSummary(allItems);
  }
}

export function setView(tab) {
  activeTab = tab;
  renderMain();
}

function bindMainEvents() {
  document.querySelectorAll('.room-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const raw = chip.dataset.room;
      roomFilter = raw === 'duplicates' ? 'duplicates' : parseInt(raw);
      renderMain();
    });
  });

  document.querySelectorAll('.item-card-delete').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      await fetch(`${API}/items/${id}`, { method: 'DELETE' });
      await loadItems();
    });
  });
}

async function loadItems() {
  try {
    const res = await fetch(`${API}/items`);
    const data = await res.json();
    allItems = (data.items || []).map(it => ({
      ...it,
      crop_url: it.crop_url ? `${API}${it.crop_url}` : null,
    }));
  } catch {
    allItems = [];
  }
  renderMain();
}

export function init() {
  loadItems();
}

export function getItem(id) {
  return allItems.find(it => it.id === parseInt(id)) || null;
}

export { loadItems };
