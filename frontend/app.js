import { render as renderDrawer, init as initDrawer } from './core/drawer.js';
import { render as renderHeader } from './core/header.js';
import { render as renderFooter, setActiveTab, updateItemsBadge } from './core/footer.js';
import { loadItems, setView, getItem, setFilter } from './items.js';
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

// On mobile the header is position:fixed (out of flow) so main-content needs
// its top padding bumped up by the header's rendered height.
if (window.matchMedia('(max-width: 768px)').matches) {
  const hdr = document.querySelector('.header');
  const main = document.querySelector('.main-content');
  const existingPt = parseInt(getComputedStyle(main).paddingTop, 10);
  main.style.paddingTop = (hdr.offsetHeight + existingPt) + 'px';
}

refresh();

document.getElementById('headerAddBtn').addEventListener('click', openCamera);
// headerPersonBtn leads nowhere yet

document.querySelectorAll('.bottom-nav .nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    navigate(btn.dataset.tab);
  });
});

document.body.addEventListener('click', e => {
  const btn = e.target.closest('[data-navigate]');
  if (!btn) return;
  const filter = btn.dataset.filter;
  if (filter !== undefined) setFilter(filter);
  navigate(btn.dataset.navigate);
});

document.body.addEventListener('click', e => {
  if (e.target.closest('.item-card-delete')) return;
  const card = e.target.closest('.item-card[data-id]');
  if (!card) return;
  const item = getItem(card.dataset.id);
  if (item) openItemSheet(item);
});

// Autohide header + bottom nav on scroll down (mobile only)
{
  const header = document.querySelector('.header');
  const bottomNav = document.querySelector('.bottom-nav');
  let lastY = 0;
  const DELTA = 6;     // ignore micro-jitter
  const OFFSET = 60;   // don't hide until scrolled past 60px

  window.addEventListener('scroll', () => {
    if (!window.matchMedia('(max-width: 768px)').matches) return;
    const y = window.scrollY;
    if (Math.abs(y - lastY) < DELTA) return;
    const hiding = y > lastY && y > OFFSET;
    header.classList.toggle('header--hidden', hiding);
    bottomNav.classList.toggle('bottom-nav--hidden', hiding);
    lastY = y;
  }, { passive: true });
}
