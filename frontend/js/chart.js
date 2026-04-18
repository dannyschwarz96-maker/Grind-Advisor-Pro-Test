/**
 * chart.js – Shot history chart with regression line overlay
 * Uses Chart.js (loaded via CDN in index.html)
 */

let _chartInstance = null;

/**
 * Render or update the shot chart.
 * @param {HTMLCanvasElement} canvas
 * @param {Array} shots     – raw shot objects from API
 * @param {Array} regrLine  – [{grind, time}, ...] from /api/recommend/chart-data
 * @param {number} targetTime – horizontal target line
 */
function renderShotChart(canvas, shots, regrLine = [], targetTime = 27) {
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';

  const textColor  = isDark ? '#A89070' : '#5A3A1A';
  const gridColor  = isDark ? '#2A1E12' : '#E8D8C0';
  const accentColor = '#C17B3A';
  const pointColor  = '#E09450';

  // Sort shots by grind size for the scatter
  const shotPoints = shots
    .filter(s => s.grind_size && s.extraction_time)
    .map(s => ({
      x: s.grind_size,
      y: s.extraction_time,
      rating: s.rating,
      id: s.id,
    }));

  const datasets = [
    // Shot data points
    {
      label: 'Shots',
      type:  'scatter',
      data:  shotPoints,
      backgroundColor: shotPoints.map(p =>
        p.rating >= 4 ? '#5C9E6A' :
        p.rating <= 2 ? '#C4594A' :
        pointColor
      ),
      borderColor: 'transparent',
      pointRadius: 6,
      pointHoverRadius: 8,
      order: 2,
    },
    // Regression line
    ...(regrLine.length > 0 ? [{
      label: 'ML-Regression',
      type:  'line',
      data:  regrLine.map(p => ({ x: p.grind, y: p.time })),
      borderColor: accentColor,
      borderWidth: 2,
      borderDash: [],
      pointRadius: 0,
      fill: false,
      tension: 0.3,
      order: 1,
    }] : []),
    // Target time line
    {
      label: 'Zielzeit',
      type:  'line',
      data: shotPoints.length > 0
        ? [
            { x: Math.min(...shotPoints.map(p => p.x)) - 1, y: targetTime },
            { x: Math.max(...shotPoints.map(p => p.x)) + 1, y: targetTime },
          ]
        : [],
      borderColor: '#5C9E6A',
      borderWidth: 1.5,
      borderDash: [6, 4],
      pointRadius: 0,
      fill: false,
      order: 0,
    },
  ];

  const config = {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      plugins: {
        legend: {
          labels: {
            color: textColor,
            font: { family: "'IBM Plex Mono', monospace", size: 11 },
            usePointStyle: true,
          },
        },
        tooltip: {
          backgroundColor: isDark ? '#1A1208' : '#FFF8EE',
          borderColor: accentColor,
          borderWidth: 1,
          titleColor: accentColor,
          bodyColor: textColor,
          callbacks: {
            label: ctx => {
              if (ctx.dataset.label === 'Shots') {
                const pt = ctx.raw;
                const stars = pt.rating ? '★'.repeat(pt.rating) : '—';
                return [
                  ` Mahlgrad: ${pt.x}`,
                  ` Zeit: ${pt.y}s`,
                  ` Rating: ${stars}`,
                ];
              }
              return ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}s`;
            },
          },
        },
      },
      scales: {
        x: {
          type:  'linear',
          title: { display: true, text: 'Mahlgrad', color: textColor,
                   font: { family: "'IBM Plex Mono', monospace" } },
          grid:  { color: gridColor },
          ticks: { color: textColor, font: { family: "'IBM Plex Mono', monospace" } },
        },
        y: {
          type:  'linear',
          title: { display: true, text: 'Extraktionszeit (s)', color: textColor,
                   font: { family: "'IBM Plex Mono', monospace" } },
          grid:  { color: gridColor },
          ticks: { color: textColor, font: { family: "'IBM Plex Mono', monospace" } },
        },
      },
    },
  };

  if (_chartInstance) {
    _chartInstance.destroy();
  }
  _chartInstance = new Chart(canvas, config);
  return _chartInstance;
}

function destroyChart() {
  if (_chartInstance) {
    _chartInstance.destroy();
    _chartInstance = null;
  }
}

// Re-render on theme change
document.addEventListener('themechange', () => {
  if (_chartInstance) {
    const canvas = _chartInstance.canvas;
    const data   = _chartInstance.config.data;
    // Chart.js doesn't support live theme swap easily → just update colors
    _chartInstance.update();
  }
});
