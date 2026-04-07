const API_BASE = window.GRIND_ADVISOR_API || "http://localhost:10000/api";
let token = localStorage.getItem("ga_token") || "";
let beans = [];
let shots = [];

const $ = (id) => document.getElementById(id);
const authHeaders = () => token ? { Authorization: `Bearer ${token}` } : {};

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      ...authHeaders(),
    },
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(data?.detail || res.statusText);
  return data;
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2200);
}

async function refreshSession() {
  if (!token) return showAuth();
  try {
    const me = await api("/auth/me");
    $("meName").textContent = me.display_name;
    $("authView").classList.add("hidden");
    $("appView").classList.remove("hidden");
    $("logoutBtn").classList.remove("hidden");
    await loadAll();
  } catch {
    localStorage.removeItem("ga_token");
    token = "";
    showAuth();
  }
}

function showAuth() {
  $("authView").classList.remove("hidden");
  $("appView").classList.add("hidden");
  $("logoutBtn").classList.add("hidden");
}

async function loadAll() {
  [beans, shots] = await Promise.all([api("/beans"), api("/shots")]);
  renderBeans();
  renderShots();
  renderBeanSelects();
  $("statBeans").textContent = beans.length;
  $("statShots").textContent = shots.length;
}

function renderBeans() {
  $("beansList").innerHTML = beans.map(b => `
    <div class="row">
      <div>
        <strong>${b.name}</strong>
        <div class="small">${b.roaster || "–"} · ${b.roast_level}</div>
      </div>
    </div>
  `).join("") || '<div class="small">Noch keine Bohnen.</div>';
}

function renderShots() {
  $("shotsList").innerHTML = shots.slice(0, 20).map(s => `
    <div class="row">
      <div>
        <strong>${beanName(s.bean_id)}</strong>
        <div class="small">${s.actual_time}s · Grind ${s.grind} · ${new Date(s.date).toLocaleString()}</div>
      </div>
    </div>
  `).join("") || '<div class="small">Noch keine Shots.</div>';
}

function beanName(id) {
  return beans.find(b => b.id === id)?.name || "Unbekannt";
}

function renderBeanSelects() {
  const options = '<option value="">– Bohne –</option>' + beans.map(b => `<option value="${b.id}">${b.name} (${b.roast_level})</option>`).join("");
  $("shotBean").innerHTML = options;
  $("predictBean").innerHTML = options;
}

document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.remove("hidden");
  });
});

$("registerBtn").onclick = async () => {
  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        display_name: $("registerName").value,
        email: $("registerEmail").value,
        password: $("registerPassword").value,
      }),
    });
    token = data.access_token;
    localStorage.setItem("ga_token", token);
    toast("Konto erstellt");
    await refreshSession();
  } catch (e) { toast(e.message); }
};

$("loginBtn").onclick = async () => {
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: $("loginEmail").value,
        password: $("loginPassword").value,
      }),
    });
    token = data.access_token;
    localStorage.setItem("ga_token", token);
    toast("Eingeloggt");
    await refreshSession();
  } catch (e) { toast(e.message); }
};

$("logoutBtn").onclick = () => {
  token = "";
  localStorage.removeItem("ga_token");
  showAuth();
};

$("saveBeanBtn").onclick = async () => {
  try {
    await api("/beans", {
      method: "POST",
      body: JSON.stringify({
        name: $("beanName").value,
        roaster: $("beanRoaster").value || null,
        origin: $("beanOrigin").value || null,
        roast_level: $("beanRoast").value,
        cupping: $("beanCupping").value || null,
      }),
    });
    toast("Bohne gespeichert");
    ["beanName","beanRoaster","beanOrigin","beanCupping"].forEach(id => $(id).value = "");
    await loadAll();
  } catch (e) { toast(e.message); }
};

$("saveShotBtn").onclick = async () => {
  try {
    await api("/shots", {
      method: "POST",
      body: JSON.stringify({
        bean_id: $("shotBean").value,
        grind: Number($("shotGrind").value),
        actual_time: Number($("shotTime").value),
        target_time: $("shotTarget").value ? Number($("shotTarget").value) : null,
        dose: $("shotDose").value ? Number($("shotDose").value) : null,
        yield_g: $("shotYield").value ? Number($("shotYield").value) : null,
        machine: $("shotMachine").value || null,
        notes: $("shotNotes").value || null,
      }),
    });
    toast("Shot gespeichert");
    ["shotGrind","shotTime","shotTarget","shotDose","shotYield","shotMachine","shotNotes"].forEach(id => $(id).value = "");
    await loadAll();
  } catch (e) { toast(e.message); }
};

$("predictBtn").onclick = async () => {
  try {
    const pred = await api("/predict", {
      method: "POST",
      body: JSON.stringify({
        bean_id: $("predictBean").value,
        target_time: Number($("predictTarget").value),
        dose: Number($("predictDose").value || 18),
      }),
    });
    const box = $("predictResult");
    box.classList.remove("hidden");
    box.textContent =
      `ML-Empfehlung: ${pred.grind}\n` +
      `Band: ${pred.grind_lo ?? "–"} bis ${pred.grind_hi ?? "–"}\n` +
      `Konfidenz: ${pred.confidence}%\n` +
      `Level: ${pred.model_level}\n` +
      pred.explanation;
  } catch (e) { toast(e.message); }
};

$("parseImportBtn").onclick = async () => {
  try {
    const file = $("importFile").files[0];
    if (!file) return toast("Bitte eine Datei wählen");
    const raw_json = await file.text();
    const parsed = await api("/import/parse", {
      method: "POST",
      body: JSON.stringify({ raw_json }),
    });
    const box = $("importResult");
    box.classList.remove("hidden");
    box.textContent = JSON.stringify(parsed, null, 2);
  } catch (e) { toast(e.message); }
};

refreshSession();
