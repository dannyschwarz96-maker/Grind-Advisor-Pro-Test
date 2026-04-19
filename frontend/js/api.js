/**
 * api.js – Typed API client for Grind Advisor backend
 *
 * Render Free Tier cold start strategy:
 *   - Ping /health immediately on load (fire-and-forget)
 *   - Show warm-up notice if first request takes > 3s
 */

// ── Config ────────────────────────────────────────────────────────────────────
// In production, set this to your Render backend URL.
// For local dev, use http://localhost:5000
const BACKEND_URL = window.BACKEND_URL || 'https://YOUR-APP.onrender.com';

const TOKEN_KEY = 'ga-token';

// ── Token management ──────────────────────────────────────────────────────────
function getToken()         { return localStorage.getItem(TOKEN_KEY); }
function setToken(t)        { localStorage.setItem(TOKEN_KEY, t); }
function clearToken()       { localStorage.removeItem(TOKEN_KEY); }
function isAuthenticated()  { return !!getToken(); }

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 204) return null;  // health / delete etc.

  const data = await res.json().catch(() => ({ error: 'Invalid JSON response' }));

  if (!res.ok) {
    const err = new Error(data.error || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

// ── Keep-alive / warm-up ──────────────────────────────────────────────────────
let _warmed = false;

async function warmupBackend() {
  if (_warmed) return;
  try {
    const start = Date.now();
    await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(15000),
    });
    const elapsed = Date.now() - start;
    _warmed = true;
    if (elapsed > 2000) {
      console.info(`[API] Backend cold start took ${elapsed}ms`);
    }
  } catch {
    // Silently ignore – backend might not be up yet
  }
}

// Warm up immediately
warmupBackend();

// ── Auth API ──────────────────────────────────────────────────────────────────
const Auth = {
  async register(email, password) {
    const data = await apiFetch('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(data.token);
    return data;
  },

  async login(email, password) {
    const data = await apiFetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(data.token);
    return data;
  },

  async me() {
    return apiFetch('/api/auth/me');
  },

  logout() {
    clearToken();
  },
};

// ── Shots API ─────────────────────────────────────────────────────────────────
const Shots = {
  async list(beanId = null) {
    const qs = beanId ? `?bean_id=${beanId}` : '';
    return apiFetch(`/api/shots/${qs}`);
  },

  async create(shotData) {
    return apiFetch('/api/shots/', {
      method: 'POST',
      body: JSON.stringify(shotData),
    });
  },

  async delete(shotId) {
    return apiFetch(`/api/shots/${shotId}`, { method: 'DELETE' });
  },

  async importJSON(jsonData) {
    return apiFetch('/api/shots/import', {
      method: 'POST',
      body: JSON.stringify(jsonData),
    });
  },

  async getCurve(shotId) {
    return apiFetch(`/api/shots/${shotId}/curve`);
  },
};

// ── Beans API ─────────────────────────────────────────────────────────────────
const Beans = {
  async list() {
    return apiFetch('/api/beans/');
  },

  async create(beanData) {
    return apiFetch('/api/beans/', {
      method: 'POST',
      body: JSON.stringify(beanData),
    });
  },

  async delete(beanId) {
    return apiFetch(`/api/beans/${beanId}`, { method: 'DELETE' });
  },
};

// ── Recommendation API ────────────────────────────────────────────────────────
const Recommend = {
  async getRecommendation({ targetTime, brewWeight, dose, roast }) {
    return apiFetch('/api/recommend', {
      method: 'POST',
      body: JSON.stringify({
        target_time: targetTime,
        brew_weight: brewWeight,
        dose,
        roast,
      }),
    });
  },

  async getChartData({ brewWeight, dose, roast }) {
    const qs = new URLSearchParams({
      brew_weight: brewWeight,
      dose,
      roast,
    });
    return apiFetch(`/api/recommend/chart-data?${qs}`);
  },

  async getModelStatus() {
    return apiFetch('/api/recommend/model-status');
  },
};
