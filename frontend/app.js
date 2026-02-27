import { render as renderDrawer, init as initDrawer } from './core/drawer.js';
import { render as renderHeader } from './core/header.js';
import { render as renderFooter, setActiveTab, updateItemsBadge } from './core/footer.js';
import { loadItems, setView, getItem } from './items.js';
import { init as initCamera, open as openCamera } from './core/camera.js';
import { init as initItemSheet, open as openItemSheet } from './core/item-sheet.js';

document.body.innerHTML = `
  ${renderDrawer()}
  ${renderHeader()}
  <main class="main-content"></main>
  ${renderFooter()}
`;

async function refresh() {
  await loadItems();
  const count = document.querySelectorAll('.item-card').length;
  updateItemsBadge(count);
}

function navigate(tab) {
  setView(tab);
  setActiveTab(tab);
  document.querySelectorAll('.drawer-menu [data-nav]').forEach(el => {
    const active = tab === 'home' ? el.dataset.nav === 'dashboard' : el.dataset.nav === tab;
    el.classList.toggle('active', active);
  });
}

initDrawer(openCamera, navigate);
initCamera(refresh);
initItemSheet(refresh);
refresh();

document.querySelectorAll('.bottom-nav .nav-item').forEach(btn => {
  btn.addEventListener('click', () => navigate(btn.dataset.tab));
});

document.body.addEventListener('click', e => {
  const btn = e.target.closest('[data-navigate]');
  if (btn) navigate(btn.dataset.navigate);
});

document.body.addEventListener('click', e => {
  if (e.target.closest('.item-card-delete')) return;
  const card = e.target.closest('.item-card[data-id]');
  if (!card) return;
  const item = getItem(card.dataset.id);
  if (item) openItemSheet(item);
});
