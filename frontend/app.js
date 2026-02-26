import { render as renderDrawer, init as initDrawer } from './core/drawer.js';
import { render as renderHeader } from './core/header.js';
import { render as renderFooter, setActiveTab, updateItemsBadge } from './core/footer.js';
import { loadItems } from './items.js';
import { init as initCamera, open as openCamera } from './core/camera.js';

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

initDrawer(openCamera);
initCamera(refresh);
refresh();

document.querySelectorAll('.bottom-nav .nav-item').forEach(btn => {
  btn.addEventListener('click', () => {
    setActiveTab(btn.dataset.tab);
  });
});
