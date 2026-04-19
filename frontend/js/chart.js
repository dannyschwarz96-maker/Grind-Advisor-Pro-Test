/**
 * chart.js – Shot charts
 */

let _chartInstance = null;

function destroyChart() {
  if (_chartInstance) {
    _chartInstance.destroy();
    _chartInstance = null;
  }
}

function renderShotChart(canvas, shots, regrLine = [], targetTime = 27) {
  const shotPoints = shots
    .filter(s => s.grind_size && s.extraction_time)
    .map(s => ({ x: s.grind_size, y: s.extraction_time, rating: s.rating, id: s.id }));

  const datasets = [
    {
      label: 'Shots',
      type: 'scatter',
      data: shotPoints,
      pointRadius: 6,
      pointHoverRadius: 8,
      order: 2,
    },
    ...(regrLine.length ? [{
      label: 'ML-Regression',
      type: 'line',
      data: regrLine.map(p => ({ x: p.grind, y: p.time })),
      borderWidth: 2,
      pointRadius: 0,
      fill: false,
      tension: 0.3,
      order: 1,
    }] : []),
    {
      label: 'Zielzeit',
      type: 'line',
      data: shotPoints.length ? [
        { x: Math.min(...shotPoints.map(p => p.x)) - 1, y: targetTime },
        { x: Math.max(...shotPoints.map(p => p.x)) + 1, y: targetTime },
      ] : [],
      borderWidth: 1.5,
      borderDash: [6, 4],
      pointRadius: 0,
      fill: false,
      order: 0,
    },
  ];

  destroyChart();
  _chartInstance = new Chart(canvas, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: ctx => {
              if (ctx.dataset.label === 'Shots') {
                const pt = ctx.raw;
                return [`Mahlgrad: ${pt.x}`, `Zeit: ${pt.y}s`];
              }
              return `${ctx.dataset.label}: ${ctx.parsed.y}`;
            },
          },
        },
      },
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Mahlgrad' } },
        y: { type: 'linear', title: { display: true, text: 'Extraktionszeit (s)' } },
      },
    },
  });
}

function renderGaggiuinoChart(canvas, curvePayload, summary = {}) {
  const series = curvePayload?.series || {};
  const datasetConfig = [
    ['pressure', 'Druck (bar)', 'y'],
    ['targetPressure', 'Ziel-Druck (bar)', 'y'],
    ['pumpFlow', 'Pumpenfluss (ml/s)', 'y1'],
    ['targetPumpFlow', 'Ziel-Pumpenfluss (ml/s)', 'y1'],
    ['temperature', 'Temperatur (°C)', 'y2'],
    ['targetTemperature', 'Ziel-Temperatur (°C)', 'y2'],
    ['shotWeight', 'Shot-Gewicht (g)', 'y3'],
    ['weightFlow', 'Gewichtsfluss (g/s)', 'y1'],
  ];

  const datasets = datasetConfig
    .filter(([key]) => Array.isArray(series[key]) && series[key].length)
    .map(([key, label, axis]) => ({
      label,
      data: series[key],
      parsing: false,
      yAxisID: axis,
      pointRadius: 0,
      borderWidth: key.startsWith('target') ? 1.5 : 2,
      borderDash: key.startsWith('target') ? [6, 4] : undefined,
      tension: 0.2,
    }));

  destroyChart();
  _chartInstance = new Chart(canvas, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        title: {
          display: true,
          text: summary?.profile_name ? `Gaggiuino · ${summary.profile_name}` : 'Gaggiuino Shot',
        },
      },
      scales: {
        x: { type: 'linear', title: { display: true, text: 'Zeit im Shot (s)' } },
        y: { type: 'linear', position: 'left', title: { display: true, text: 'Druck' } },
        y1: { type: 'linear', position: 'right', title: { display: true, text: 'Flow' }, grid: { drawOnChartArea: false } },
        y2: { type: 'linear', position: 'right', title: { display: true, text: 'Temp' }, grid: { drawOnChartArea: false }, display: false },
        y3: { type: 'linear', position: 'right', title: { display: true, text: 'Gewicht' }, grid: { drawOnChartArea: false }, display: false },
      },
    },
  });
}
