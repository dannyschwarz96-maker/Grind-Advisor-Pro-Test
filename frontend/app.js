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
  let data = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text || null;
  }

  if (!res.ok) {
    let msg = res.statusText;

    if (data?.detail) {
      if (typeof data.detail === "string") {
        msg = data.detail;
      } else if (Array.isArray(data.detail)) {
        msg = data.detail
          .map((d) => `${(d.loc || []).join(".")}: ${d.msg}`)
          .join(" | ");
      } else {
        msg = JSON.stringify(data.detail);
      }
    } else if (typeof data === "string") {
      msg = data;
    }

    throw new Error(msg);
  }

  return data;
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 2600);
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
  const options =
    '<option value="">– Bohne –</option>' +
    beans.map(b => `<option value="${b.id}">${b.name} (${b.roast_level})</option>`).join("");
  $("shotBean").innerHTML = options;
  $("predictBean").innerHTML = options;
}

function shotsForBean(beanId) {
  return shots.filter(
    s => s.bean_id === beanId && s.grind != null && s.actual_time != null
  );
}

function calcLinearPrediction(beanShots, targetTime) {
  const pts = beanShots.filter(
    s => Number.isFinite(Number(s.grind)) && Number.isFinite(Number(s.actual_time))
  );
  if (pts.length < 2) return null;

  const xs = pts.map(p => Number(p.grind));
  const ys = pts.map(p => Number(p.actual_time));
  const n = xs.length;

  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;

  const denom = xs.reduce((sum, x) => sum + (x - mx) ** 2, 0);
  if (Math.abs(denom) < 1e-9) return null;

  const slope = xs.reduce((sum, x, i) => sum + (x - mx) * (ys[i] - my), 0) / denom;
  const intercept = my - slope * mx;

  if (!Number.isFinite(slope) || Math.abs(slope) < 1e-9) return null;

  const grindAtTarget = (targetTime - intercept) / slope;
  if (!Number.isFinite(grindAtTarget)) return null;

  return {
    grind: Number(grindAtTarget.toFixed(1)),
    intercept,
    slope,
  };
}

function drawPredictChart(beanShots, targetTime, mlGrind, linearInfo) {
  const canvas = $("predictChart");
  if (!canvas) return;

  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 700;
  const height = 260;

  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const pts = beanShots
    .map(s => ({ x: Number(s.grind), y: Number(s.actual_time) }))
    .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));

  if (!pts.length) {
    ctx.fillStyle = "#b8a99a";
    ctx.font = "14px system-ui";
    ctx.textAlign = "center";
    ctx.fillText("Noch keine Shot-Daten für diese Bohne", width / 2, height / 2);
    return;
  }

  const extrasX = [];
  if (Number.isFinite(Number(mlGrind))) extrasX.push(Number(mlGrind));
  if (linearInfo && Number.isFinite(Number(linearInfo.grind))) extrasX.push(Number(linearInfo.grind));

  const allX = pts.map(p => p.x).concat(extrasX);
  const allY = pts.map(p => p.y).concat([targetTime]);

  const minX = Math.min(...allX) - 2;
  const maxX = Math.max(...allX) + 2;
  const minY = Math.max(0, Math.min(...allY) - 4);
  const maxY = Math.max(...allY) + 4;

  const pad = { l: 44, r: 16, t: 18, b: 34 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;

  const tx = x => pad.l + ((x - minX) / Math.max(1e-9, (maxX - minX))) * plotW;
  const ty = y => pad.t + (1 - ((y - minY) / Math.max(1e-9, (maxY - minY)))) * plotH;

  // grid
  ctx.strokeStyle = "rgba(255,255,255,.08)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.t + (plotH / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad.l, y);
    ctx.lineTo(width - pad.r, y);
    ctx.stroke();
  }

  // axes
  ctx.strokeStyle = "rgba(255,255,255,.18)";
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, height - pad.b);
  ctx.lineTo(width - pad.r, height - pad.b);
  ctx.stroke();

  // y labels
  ctx.fillStyle = "#b8a99a";
  ctx.font = "11px system-ui";
  ctx.textAlign = "right";
  for (let i = 0; i <= 4; i++) {
    const val = maxY - ((maxY - minY) / 4) * i;
    const y = pad.t + (plotH / 4) * i;
    ctx.fillText(val.toFixed(0), pad.l - 6, y + 4);
  }

  // target line
  ctx.strokeStyle = "#5ba4cf";
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.moveTo(pad.l, ty(targetTime));
  ctx.lineTo(width - pad.r, ty(targetTime));
  ctx.stroke();
  ctx.setLineDash([]);

  // regression line
  if (linearInfo) {
    const x1 = minX;
    const y1 = linearInfo.intercept + linearInfo.slope * x1;
    const x2 = maxX;
    const y2 = linearInfo.intercept + linearInfo.slope * x2;

    ctx.strokeStyle = "#f0c05a";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(tx(x1), ty(y1));
    ctx.lineTo(tx(x2), ty(y2));
    ctx.stroke();
  }

  // shot points
  ctx.fillStyle = "#d98a36";
  for (const p of pts) {
    ctx.beginPath();
    ctx.arc(tx(p.x), ty(p.y), 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // ML marker
  if (Number.isFinite(Number(mlGrind))) {
    ctx.fillStyle = "#5ba4cf";
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(tx(Number(mlGrind)), ty(targetTime), 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }

  // linear marker
  if (linearInfo && Number.isFinite(Number(linearInfo.grind))) {
    const x = tx(Number(linearInfo.grind));
    const y = ty(targetTime);
    ctx.fillStyle = "#f0c05a";
    ctx.strokeStyle = "#1a0f0a";
    ctx.lineWidth = 2;
    ctx.fillRect(x - 5, y - 5, 10, 10);
    ctx.strokeRect(x - 5, y - 5, 10, 10);
  }

  // x labels
  ctx.fillStyle = "#b8a99a";
  ctx.font = "11px system-ui";
  ctx.textAlign = "center";

  const ticks = 5;
  for (let i = 0; i <= ticks; i++) {
    const xVal = minX + ((maxX - minX) / ticks) * i;
    ctx.fillText(xVal.toFixed(1), tx(xVal), height - 12);
  }

  // axis labels
  ctx.fillStyle = "#b8a99a";
  ctx.font = "12px system-ui";
  ctx.textAlign = "center";
  ctx.fillText("Mahlgrad", pad.l + plotW / 2, height - 2);

  ctx.save();
  ctx.translate(14, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Zeit (s)", 0, 0);
  ctx.restore();
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
  const display_name = $("registerName").value.trim();
  const email = $("registerEmail").value.trim();
  const password = $("registerPassword").value;

  if (display_name.length < 2) return toast("Name muss mindestens 2 Zeichen haben");
  if (!email.includes("@")) return toast("Bitte gültige E-Mail eingeben");
  if (password.length < 8) return toast("Passwort muss mindestens 8 Zeichen haben");

  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ display_name, email, password }),
    });
    token = data.access_token;
    localStorage.setItem("ga_token", token);
    toast("Konto erstellt");
    await refreshSession();
  } catch (e) {
    toast(e.message);
  }
};

$("loginBtn").onclick = async () => {
  const email = $("loginEmail").value.trim();
  const password = $("loginPassword").value;

  if (!email) return toast("Bitte E-Mail eingeben");
  if (!password) return toast("Bitte Passwort eingeben");

  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    token = data.access_token;
    localStorage.setItem("ga_token", token);
    toast("Eingeloggt");
    await refreshSession();
  } catch (e) {
    toast(e.message);
  }
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
    ["beanName", "beanRoaster", "beanOrigin", "beanCupping"].forEach(id => $(id).value = "");
    await loadAll();
  } catch (e) {
    toast(e.message);
  }
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
    ["shotGrind", "shotTime", "shotTarget", "shotDose", "shotYield", "shotMachine", "shotNotes"].forEach(id => $(id).value = "");
    await loadAll();
  } catch (e) {
    toast(e.message);
  }
};

$("predictBtn").onclick = async () => {
  try {
    const bean_id = $("predictBean").value;
    const target_time = Number($("predictTarget").value);
    const dose = Number($("predictDose").value || 18);

    if (!bean_id) return toast("Bitte eine Bohne auswählen");
    if (!Number.isFinite(target_time)) return toast("Bitte Zielzeit eingeben");

    const pred = await api("/predict", {
      method: "POST",
      body: JSON.stringify({ bean_id, target_time, dose }),
    });

    const beanShots = shotsForBean(bean_id);
    const linear = calcLinearPrediction(beanShots, target_time);

    $("predictCards").classList.remove("hidden");
    $("predictChartWrap").classList.remove("hidden");

    $("predictMlValue").textContent = pred.grind ?? "–";
    $("predictMlMeta").textContent =
      `${pred.model_level} · ${pred.confidence}% · ${pred.grind_lo ?? "–"} bis ${pred.grind_hi ?? "–"}`;

    $("predictLinValue").textContent = linear?.grind ?? "–";
    $("predictLinMeta").textContent = linear
      ? `Schnittpunkt der Regressionslinie bei ${target_time}s`
      : "Zu wenig Punkte für lineare Näherung";

    const box = $("predictResult");
    box.classList.remove("hidden");
    box.textContent =
      `ML-Empfehlung: ${pred.grind}\n` +
      `Band: ${pred.grind_lo ?? "–"} bis ${pred.grind_hi ?? "–"}\n` +
      `Konfidenz: ${pred.confidence}%\n` +
      `Level: ${pred.model_level}\n` +
      `Linear: ${linear?.grind ?? "–"}\n` +
      pred.explanation;

    drawPredictChart(beanShots, target_time, pred.grind, linear);
  } catch (e) {
    toast(e.message);
  }
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
  } catch (e) {
    toast(e.message);
  }
};

window.addEventListener("resize", () => {
  const chartWrap = $("predictChartWrap");
  const bean_id = $("predictBean")?.value;
  const target_time = Number($("predictTarget")?.value);
  const mlVal = Number(($("predictMlValue")?.textContent || "").replace(",", "."));

  if (!chartWrap || chartWrap.classList.contains("hidden") || !bean_id || !Number.isFinite(target_time)) return;
  const beanShots = shotsForBean(bean_id);
  const linear = calcLinearPrediction(beanShots, target_time);
  drawPredictChart(beanShots, target_time, mlVal, linear);
});

refreshSession();
