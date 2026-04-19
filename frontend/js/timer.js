/**
 * timer.js – Clientside shot timer with target-zone visual feedback
 * No backend calls. Target zone: 25–30s (specialty espresso standard)
 */

class ShotTimer {
  constructor({ displayEl, btnEl, outputEl, onStop }) {
    this.display  = displayEl;   // <span> showing time
    this.btn      = btnEl;       // Start/Stop/Reset button
    this.outputEl = outputEl;    // <input> to write seconds into when stopped
    this.onStop   = onStop;      // callback(seconds)

    this._startTime = null;
    this._elapsed   = 0;
    this._interval  = null;
    this._state     = 'idle'; // idle | running | stopped

    this._render();
  }

  // ── Public API ──────────────────────────────────────────────────────────────
  handleClick() {
    switch (this._state) {
      case 'idle':    this._start(); break;
      case 'running': this._stop();  break;
      case 'stopped': this._reset(); break;
    }
  }

  reset() {
    this._reset();
  }

  // ── Private ─────────────────────────────────────────────────────────────────
  _start() {
    this._startTime = Date.now() - this._elapsed;
    this._state = 'running';
    this._interval = setInterval(() => this._tick(), 50);
    this._render();
  }

  _stop() {
    clearInterval(this._interval);
    this._interval = null;
    this._state = 'stopped';

    const secs = this._elapsed / 1000;

    // Write into the extraction time input
    if (this.outputEl) {
      this.outputEl.value = secs.toFixed(1);
      this.outputEl.dispatchEvent(new Event('input'));
    }

    if (this.onStop) this.onStop(secs);
    this._render();
  }

  _reset() {
    clearInterval(this._interval);
    this._interval = null;
    this._elapsed  = 0;
    this._state    = 'idle';

    if (this.outputEl) {
      this.outputEl.value = '';
      this.outputEl.dispatchEvent(new Event('input'));
    }

    this._render();
  }

  _tick() {
    this._elapsed = Date.now() - this._startTime;
    this._render();
  }

  _render() {
    const secs = this._elapsed / 1000;
    const formatted = `${secs.toFixed(1)}s`;

    if (this.display) {
      this.display.textContent = formatted;

      // Remove all state classes
      this.display.classList.remove('timer--good', 'timer--warn', 'timer--over', 'timer--idle');

      if (this._state === 'idle') {
        this.display.classList.add('timer--idle');
      } else if (secs < 25) {
        // Running, before target zone
        this.display.classList.add('timer--running');
      } else if (secs <= 30) {
        // In the sweet spot
        this.display.classList.add('timer--good');
      } else {
        // Over-extracted
        this.display.classList.add('timer--over');
      }
    }

    if (this.btn) {
      const labels = { idle: 'timer_start', running: 'timer_stop', stopped: 'timer_reset' };
      this.btn.dataset.i18n = labels[this._state];
      this.btn.textContent = t(labels[this._state]);
    }
  }
}
