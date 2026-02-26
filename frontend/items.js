import { render as renderSummary } from './objects/summary.js';
import { render as renderItemsList } from './objects/items-list.js';

const API = 'http://localhost:5000';

let allItems = [];
let roomFilter = 0;

function renderMain() {
  const main = document.querySelector('.main-content');
  main.innerHTML = `
    ${renderSummary(allItems)}
    ${renderItemsList(allItems, roomFilter)}
  `;
  bindMainEvents();
}

function bindMainEvents() {
  document.querySelectorAll('.room-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      roomFilter = parseInt(chip.dataset.room);
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
    allItems = data.items || [];
  } catch {
    allItems = [];
  }
  renderMain();
}

export function init() {
  loadItems();
}

export { loadItems };
