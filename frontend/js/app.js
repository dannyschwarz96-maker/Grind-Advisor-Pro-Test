/**
 * app.js – Grind Advisor Pro · Main Application Logic
 * Single-Page App: Auth → Dashboard (Shots / Beans / Recommend / Import)
 */

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  user:        null,
  token:       null,
  beans:       [],
  shots:       [],
  currentTab:  'shots',
  shotTimer:   null,
  chart:       null,
};

// ── DOM Refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  applyTheme(getPreferredTheme());
  applyTranslations();
  bindStaticEvents();

  if (isAuthenticated()) {
    try {
      const { user } = await Auth.me().then(u => ({ user: u }));
      state.user = user;
      showApp();
      await Promise.all([loadBeans(), loadShots()]);
    } catch {
      clearToken();
      showAuth('login');
    }
  } else {
    showAuth('login');
  }
});

// ── Auth flow ─────────────────────────────────────────────────────────────────
function showAuth(mode = 'login') {
  $('app').classList.add('hidden');
  $('auth-overlay').classList.remove('hidden');
  switchAuthMode(mode);
}

function showApp() {
  $('auth-overlay').classList.add('hidden');
  $('app').classList.remove('hidden');
  updateUserBadge();
  switchTab(state.currentTab);
}

function switchAuthMode(mode) {
  $('login-panel').classList.toggle('hidden', mode !== 'login');
  $('register-panel').classList.toggle('hidden', mode !== 'register');
}

async function handleLogin(e) {
  e.preventDefault();
  const email    = $('login-email').value.trim();
  const password = $('login-password').value;
  const btn      = $('login-btn');
  setLoading(btn, true);
  clearError('login-error');
  try {
    const { user } = await Auth.login(email, password);
    state.user = user;
    showApp();
    await Promise.all([loadBeans(), loadShots()]);
  } catch (err) {
    showError('login-error', err.message);
  } finally {
    setLoading(btn, false);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const email    = $('reg-email').value.trim();
  const password = $('reg-password').value;
  const btn      = $('register-btn');

  if (password.length < 8) {
    showError('reg-error', t('password_hint'));
    return;
  }

  setLoading(btn, true);
  clearError('reg-error');
  try {
    const { user } = await Auth.register(email, password);
    state.user = user;
    showApp();
    await Promise.all([loadBeans(), loadShots()]);
  } catch (err) {
    showError('reg-error', err.message);
  } finally {
    setLoading(btn, false);
  }
}

function handleLogout() {
  Auth.logout();
  state.user  = null;
  state.beans = [];
  state.shots = [];
  destroyChart();
  showAuth('login');
}

// ── Tab navigation ─────────────────────────────────────────────────────────────
function switchTab(tab) {
  state.currentTab = tab;
  $$('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  $$('.tab-panel').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== tab));

  if (tab === 'shots')     onShotsTab();
  if (tab === 'recommend') onRecommendTab();
}

// ── Shots tab ─────────────────────────────────────────────────────────────────
async function loadShots() {
  try {
    state.shots = await Shots.list();
    renderShotList();
    updateStatsBar();
  } catch (err) {
    console.error('Failed to load shots', err);
  }
}

function onShotsTab() {
  populateBeanSelect('shot-bean-id');
  renderShotList();
  initTimer();
}

function renderShotList() {
  const container = $('shot-list');
  const canvas    = $('shot-chart-canvas');

  if (!state.shots.length) {
    container.innerHTML = `<p class="empty-state" data-i18n="no_shots">${t('no_shots')}</p>`;
    if (canvas) canvas.parentElement.classList.add('hidden');
    return;
  }

  if (canvas) {
    canvas.parentElement.classList.remove('hidden');
    renderChart();
  }

  container.innerHTML = state.shots.map(s => shotCard(s)).join('');
  container.querySelectorAll('.shot-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteShot(btn.dataset.id));
  });
}

function shotCard(s) {
  const ratio    = s.brew_ratio ? `${s.brew_ratio.toFixed(2)}:1` : '—';
  const stars    = s.rating ? '★'.repeat(s.rating) + '☆'.repeat(5 - s.rating) : '—';
  const beanName = s.bean_name || t('no_bean');
  const date     = s.created_at
    ? new Date(s.created_at).toLocaleDateString(getLang() === 'de' ? 'de-DE' : 'en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : '';

  const timeClass = s.extraction_time < 20 ? 'time--fast'
                  : s.extraction_time > 35 ? 'time--slow'
                  : s.extraction_time >= 25 && s.extraction_time <= 30 ? 'time--good'
                  : '';

  return `
    <article class="shot-card">
      <div class="shot-card__grind">
        <span class="grind-value">${s.grind_size}</span>
        <span class="grind-label">Grind</span>
      </div>
      <div class="shot-card__body">
        <div class="shot-card__row">
          <span class="shot-stat ${timeClass}">
            <span class="shot-stat__val">${s.extraction_time}s</span>
            <span class="shot-stat__key">Zeit</span>
          </span>
          ${s.brew_weight ? `<span class="shot-stat">
            <span class="shot-stat__val">${s.brew_weight}g</span>
            <span class="shot-stat__key">Output</span>
          </span>` : ''}
          <span class="shot-stat">
            <span class="shot-stat__val">${ratio}</span>
            <span class="shot-stat__key">Ratio</span>
          </span>
          <span class="shot-stat">
            <span class="shot-stat__val">${stars}</span>
            <span class="shot-stat__key">Rating</span>
          </span>
        </div>
        <div class="shot-card__meta">
          <span class="bean-badge">${beanName}</span>
          ${s.notes ? `<span class="shot-notes">${escHtml(s.notes)}</span>` : ''}
          <span class="shot-date">${date}</span>
        </div>
      </div>
      <button class="shot-delete icon-btn" data-id="${s.id}" title="${t('delete')}">✕</button>
    </article>
  `;
}

async function handleShotSubmit(e) {
  e.preventDefault();
  const btn = $('save-shot-btn');
  setLoading(btn, true);
  clearError('shot-error');

  const grind = parseFloat($('shot-grind').value);
  const time  = parseFloat($('shot-time').value);

  if (isNaN(grind) || grind <= 0) {
    showError('shot-error', t('grind_hint'));
    setLoading(btn, false);
    return;
  }
  if (isNaN(time) || time <= 0) {
    showError('shot-error', t('extraction_hint'));
    setLoading(btn, false);
    return;
  }

  try {
    const shot = await Shots.create({
      grind_size:      grind,
      extraction_time: time,
      brew_weight:     parseFloatOrNull($('shot-brew-weight').value),
      dose:            parseFloatOrNull($('shot-dose').value) || 18,
      bean_id:         $('shot-bean-id').value || null,
      rating:          parseInt($('shot-rating').value) || null,
      notes:           $('shot-notes').value.trim() || null,
    });

    state.shots.unshift(shot);
    renderShotList();
    updateStatsBar();
    e.target.reset();
    if (state.shotTimer) state.shotTimer.reset();
    showToast(t('success'));
  } catch (err) {
    showError('shot-error', err.message);
  } finally {
    setLoading(btn, false);
  }
}

async function deleteShot(id) {
  if (!confirm(t('delete_confirm'))) return;
  try {
    await Shots.delete(id);
    state.shots = state.shots.filter(s => s.id !== id);
    renderShotList();
    updateStatsBar();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── Timer ─────────────────────────────────────────────────────────────────────
function initTimer() {
  if (state.shotTimer) return;
  const display = $('timer-display');
  const btn     = $('timer-btn');
  const output  = $('shot-time');
  if (!display || !btn) return;

  state.shotTimer = new ShotTimer({
    displayEl: display,
    btnEl:     btn,
    outputEl:  output,
    onStop:    secs => {
      $('shot-time').focus();
    },
  });

  btn.addEventListener('click', () => state.shotTimer.handleClick());
}

// ── Chart ─────────────────────────────────────────────────────────────────────
async function renderChart() {
  const canvas = $('shot-chart-canvas');
  if (!canvas || !state.shots.length) return;

  let regrLine  = [];
  let targetTime = 27;

  try {
    const data = await Recommend.getChartData({
      brewWeight: 36, dose: 18, roast: 'medium',
    });
    regrLine  = data.regression_line || [];
  } catch { /* Model might not exist yet, chart renders without regression */ }

  renderShotChart(canvas, state.shots, regrLine, targetTime);
}

// ── Beans tab ─────────────────────────────────────────────────────────────────
async function loadBeans() {
  try {
    state.beans = await Beans.list();
    renderBeanList();
    populateBeanSelect('shot-bean-id');
    populateBeanSelect('rec-bean-select');
  } catch (err) {
    console.error('Failed to load beans', err);
  }
}

function renderBeanList() {
  const container = $('bean-list');
  if (!state.beans.length) {
    container.innerHTML = `<p class="empty-state" data-i18n="no_beans">${t('no_beans')}</p>`;
    return;
  }
  container.innerHTML = state.beans.map(b => beanCard(b)).join('');
  container.querySelectorAll('.bean-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteBean(btn.dataset.id));
  });
}

function beanCard(b) {
  const roastEmoji = { light: '🌤', medium: '☁️', dark: '🌑' }[b.roast] || '•';
  return `
    <article class="bean-card">
      <div class="bean-card__roast">${roastEmoji}</div>
      <div class="bean-card__body">
        <h3 class="bean-card__name">${escHtml(b.name)}</h3>
        <div class="bean-card__meta">
          <span class="roast-badge roast-badge--${b.roast}">${t('roast_' + b.roast)}</span>
          ${b.origin ? `<span class="origin-badge">${escHtml(b.origin)}</span>` : ''}
          <span class="shot-count-badge">${t('shots_count', { n: b.shot_count || 0 })}</span>
        </div>
      </div>
      <button class="bean-delete icon-btn" data-id="${b.id}" title="${t('delete')}">✕</button>
    </article>
  `;
}

async function handleBeanSubmit(e) {
  e.preventDefault();
  const btn = $('save-bean-btn');
  setLoading(btn, true);
  clearError('bean-error');
  try {
    const bean = await Beans.create({
      name:   $('bean-name').value.trim(),
      roast:  $('bean-roast').value,
      origin: $('bean-origin').value.trim() || null,
    });
    state.beans.unshift({ ...bean, shot_count: 0 });
    renderBeanList();
    populateBeanSelect('shot-bean-id');
    populateBeanSelect('rec-bean-select');
    e.target.reset();
    showToast(t('success'));
  } catch (err) {
    showError('bean-error', err.message);
  } finally {
    setLoading(btn, false);
  }
}

async function deleteBean(id) {
  if (!confirm(t('delete_confirm'))) return;
  try {
    await Beans.delete(id);
    state.beans = state.beans.filter(b => b.id !== id);
    renderBeanList();
    populateBeanSelect('shot-bean-id');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function populateBeanSelect(selectId) {
  const sel = $(selectId);
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = `<option value="">${t('select_bean')}</option>` +
    state.beans.map(b =>
      `<option value="${b.id}"${b.id === current ? ' selected' : ''}>${escHtml(b.name)} (${t('roast_' + b.roast)})</option>`
    ).join('');
}

// ── Recommendation tab ────────────────────────────────────────────────────────
function onRecommendTab() {
  populateBeanSelect('rec-bean-select');
  checkModelStatus();
}

async function checkModelStatus() {
  const badge = $('model-status-badge');
  if (!badge) return;
  try {
    const status = await Recommend.getModelStatus();
    if (status.has_model) {
      badge.textContent = t('model_info', { n: status.n_samples, r2: (status.r2_score || 0).toFixed(2) });
      badge.className = 'model-badge model-badge--ok';
    } else {
      badge.textContent = t('no_model');
      badge.className = 'model-badge model-badge--warn';
    }
  } catch {
    badge.textContent = '—';
  }
}

async function handleRecommend(e) {
  e.preventDefault();
  const btn = $('recommend-btn');
  setLoading(btn, true);
  clearError('rec-error');
  $('rec-result').classList.add('hidden');

  const beanId = $('rec-bean-select').value;
  const selectedBean = state.beans.find(b => b.id === beanId);
  const roast = selectedBean?.roast || 'medium';

  try {
    const result = await Recommend.getRecommendation({
      targetTime:  parseFloat($('rec-target-time').value) || 27,
      brewWeight:  parseFloat($('rec-brew-weight').value) || 36,
      dose:        parseFloat($('rec-dose').value) || 18,
      roast,
    });

    if (result.error) {
      const needed = result.training_meta?.shots_needed || 3;
      showError('rec-error', t('need_more_shots', { n: needed }));
      return;
    }

    $('rec-grind-value').textContent    = result.optimal_grind;
    $('rec-time-value').textContent     = `${result.predicted_time}s`;
    $('rec-confidence-value').textContent = t(`confidence_${result.confidence}`);
    $('rec-confidence-value').className = `confidence-badge confidence--${result.confidence}`;

    const noteEl = $('rec-direction-note');
    if (result.direction_hint) {
      noteEl.textContent = t(`direction_${result.direction_hint}`);
      noteEl.classList.remove('hidden');
    } else {
      noteEl.classList.add('hidden');
    }

    $('rec-model-info').textContent = t('model_info', {
      n:  result.n_samples,
      r2: (result.r2_score || 0).toFixed(2),
    });

    $('rec-result').classList.remove('hidden');
    $('rec-result').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Animate the grind number
    animateNumber($('rec-grind-value'), 0, result.optimal_grind, 600);

  } catch (err) {
    showError('rec-error', err.message || t('error'));
  } finally {
    setLoading(btn, false);
  }
}

// ── Import tab ────────────────────────────────────────────────────────────────
function initImport() {
  const dropzone = $('import-dropzone');
  const fileInput = $('import-file');
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) processImportFile(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) processImportFile(fileInput.files[0]);
  });
}

async function processImportFile(file) {
  const resultEl = $('import-result');
  resultEl.className = 'import-result';
  resultEl.textContent = t('loading');

  try {
    const text = await file.text();
    const json = JSON.parse(text);

    const result = await Shots.importJSON(json);

    if (result.imported > 0) {
      resultEl.className = 'import-result import-result--success';
      resultEl.textContent =
        `${t('import_success', { n: result.imported })}` +
        (result.skipped > 0 ? ` · ${t('import_skipped', { n: result.skipped })}` : '');
      await loadShots();
    } else {
      resultEl.className = 'import-result import-result--warn';
      resultEl.textContent = t('import_skipped', { n: result.skipped });
    }

    if (result.errors?.length) {
      console.warn('Import errors:', result.errors);
    }
  } catch (err) {
    resultEl.className = 'import-result import-result--error';
    resultEl.textContent = err.message || t('error');
  }
}

// ── UI Helpers ────────────────────────────────────────────────────────────────
function updateUserBadge() {
  const el = $('user-email');
  if (el && state.user) el.textContent = state.user.email;
}

function updateStatsBar() {
  const el = $('stats-shots');
  if (el) el.textContent = t('shots_saved', { n: state.shots.length });
}

function setLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.classList.toggle('loading', loading);
}

function showError(elId, msg) {
  const el = $(elId);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function clearError(elId) {
  const el = $(elId);
  if (!el) return;
  el.textContent = '';
  el.classList.add('hidden');
}

function showToast(msg, type = 'success') {
  let toast = $('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `toast toast--${type} toast--visible`;
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => toast.classList.remove('toast--visible'), 2500);
}

function parseFloatOrNull(val) {
  const f = parseFloat(val);
  return isNaN(f) ? null : f;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function animateNumber(el, from, to, duration) {
  const start = performance.now();
  const update = now => {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = (from + (to - from) * ease).toFixed(1);
    if (p < 1) requestAnimationFrame(update);
    else el.textContent = to;
  };
  requestAnimationFrame(update);
}

// ── Event Bindings ────────────────────────────────────────────────────────────
function bindStaticEvents() {
  // Auth forms
  $('login-form')?.addEventListener('submit', handleLogin);
  $('register-form')?.addEventListener('submit', handleRegister);
  $('to-register')?.addEventListener('click', () => switchAuthMode('register'));
  $('to-login')?.addEventListener('click', () => switchAuthMode('login'));
  $('logout-btn')?.addEventListener('click', handleLogout);

  // Theme & lang toggles
  $('theme-toggle')?.addEventListener('click', toggleTheme);
  $('lang-toggle')?.addEventListener('click', () => {
    setLang(getLang() === 'de' ? 'en' : 'de');
  });

  // Tab nav
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Shot form
  $('shot-form')?.addEventListener('submit', handleShotSubmit);

  // Star rating
  $$('.star-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = parseInt(btn.dataset.val);
      $('shot-rating').value = val;
      $$('.star-btn').forEach((b, i) => b.classList.toggle('active', i < val));
    });
  });

  // Bean form
  $('bean-form')?.addEventListener('submit', handleBeanSubmit);

  // Recommendation form
  $('recommend-form')?.addEventListener('submit', handleRecommend);

  // Import
  initImport();

  // Lang change → re-translate dynamic content
  document.addEventListener('langchange', () => {
    renderShotList();
    renderBeanList();
  });
}
