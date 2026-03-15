/**
 * tests/test_browser_detection.js
 * ─────────────────────────────────────────────────────────────
 * Unit tests for the browser anti-cheat detection functions in
 * static/js/exam.js.  Runs with Node.js + jsdom (no bundler needed).
 *
 * Install deps once:
 *   npm install --save-dev jest jest-environment-jsdom
 *
 * Run:
 *   npx jest tests/test_browser_detection.js
 */

/* ── jsdom environment setup ────────────────────────────────── */
// @jest-environment jsdom

const fs   = require('fs');
const path = require('path');

/* ── Minimal stubs that exam.js depends on ─────────────────── */

// SESSION_ID is injected by Flask in the real page
global.SESSION_ID = 42;

// io() stub (Socket.IO)
global.io = () => ({ on: jest.fn() });

// TOTAL_Q is set by Flask
global.TOTAL_Q = 10;

// Stub fetch so no real HTTP calls are made
global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));

// Stub addViol (declared in exam.js but needs DOM element)
const violFeedEl = document.createElement('div');
violFeedEl.id = 'viols-feed';
document.body.appendChild(violFeedEl);
global.addViol = jest.fn();    // will be overridden once exam.js loads

// Stub nowStr (used by addViol)
global.nowStr = () => '00:00';

// Load exam.js into the jsdom context
const examJsPath = path.resolve(__dirname, '../static/js/exam.js');
const examJsCode = fs.readFileSync(examJsPath, 'utf8');
// Wrap to avoid top-level setInterval / io() issues during import
try { eval(examJsCode); } catch (_) { /* DOMContentLoaded listeners are fine */ }


/* ═══════════════════════════════════════════════════════════════
   TEST SUITE 1 — sendBrowserViolation helper
═══════════════════════════════════════════════════════════════ */
describe('sendBrowserViolation', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('calls fetch with correct URL', () => {
    sendBrowserViolation('clipboard_access', 'copy attempt');
    expect(fetch).toHaveBeenCalledWith(
      `/browser/violation/${SESSION_ID}`,
      expect.objectContaining({ method: 'POST' })
    );
  });

  test('sends JSON body with violation_type and details', () => {
    sendBrowserViolation('window_focus_lost', 'blur event');
    const [, init] = fetch.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(body.violation_type).toBe('window_focus_lost');
    expect(body.details).toBe('blur event');
  });

  test('includes ISO timestamp in payload', () => {
    sendBrowserViolation('rapid_tab_switch', 'fast');
    const [, init] = fetch.mock.calls[0];
    const body = JSON.parse(init.body);
    expect(body.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  test('does not throw when SESSION_ID is undefined', () => {
    const orig = global.SESSION_ID;
    global.SESSION_ID = undefined;
    expect(() => sendBrowserViolation('clipboard_access', 'x')).not.toThrow();
    global.SESSION_ID = orig;
    fetch.mockClear();
  });
});


/* ═══════════════════════════════════════════════════════════════
   TEST SUITE 2 — Clipboard detection
═══════════════════════════════════════════════════════════════ */
describe('Clipboard detection', () => {
  beforeEach(() => fetch.mockClear());

  test('copy event triggers clipboard_access violation', () => {
    document.dispatchEvent(new Event('copy'));
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/browser/violation/'),
      expect.objectContaining({ method: 'POST' })
    );
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.violation_type).toBe('clipboard_access');
    expect(body.details).toMatch(/copy/i);
  });

  test('cut event triggers clipboard_access violation', () => {
    document.dispatchEvent(new Event('cut'));
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.violation_type).toBe('clipboard_access');
    expect(body.details).toMatch(/cut/i);
  });

  test('paste event triggers clipboard_access violation', () => {
    document.dispatchEvent(new Event('paste'));
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.violation_type).toBe('clipboard_access');
    expect(body.details).toMatch(/paste/i);
  });

  test('each clipboard event produces exactly one fetch call', () => {
    document.dispatchEvent(new Event('copy'));
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});


/* ═══════════════════════════════════════════════════════════════
   TEST SUITE 3 — Focus loss / rapid tab switch detection
═══════════════════════════════════════════════════════════════ */
describe('Focus loss detection (_trackFocusLoss)', () => {
  beforeEach(() => {
    fetch.mockClear();
    // Reset internal counter by reassigning — the real code uses _focusLossTimes
    if (typeof _focusLossTimes !== 'undefined') {
      _focusLossTimes.length = 0;
    }
  });

  test('single focus loss sends window_focus_lost', () => {
    _trackFocusLoss('window_focus_lost', 'blur');
    const calls = fetch.mock.calls.filter(c => c[0].includes('/browser/violation/'));
    expect(calls.length).toBeGreaterThanOrEqual(1);
    const body = JSON.parse(calls[0][1].body);
    expect(body.violation_type).toBe('window_focus_lost');
  });

  test('3rd focus loss in 30s escalates to rapid_tab_switch', () => {
    // Call twice first (these should send window_focus_lost)
    _trackFocusLoss('window_focus_lost', 'blur 1');
    _trackFocusLoss('window_focus_lost', 'blur 2');
    fetch.mockClear();

    // Third call should trigger rapid_tab_switch
    _trackFocusLoss('window_focus_lost', 'blur 3');
    const calls = fetch.mock.calls.filter(c => c[0].includes('/browser/violation/'));
    expect(calls.length).toBe(1);
    const body = JSON.parse(calls[0][1].body);
    expect(body.violation_type).toBe('rapid_tab_switch');
  });

  test('counter resets after rapid_tab_switch is reported', () => {
    // Fill up the counter (3 events → rapid_tab_switch)
    _trackFocusLoss('window_focus_lost', 'a');
    _trackFocusLoss('window_focus_lost', 'b');
    _trackFocusLoss('window_focus_lost', 'c');
    fetch.mockClear();

    // Now a single focus loss should be window_focus_lost again
    _trackFocusLoss('window_focus_lost', 'd');
    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.violation_type).toBe('window_focus_lost');
  });
});


/* ═══════════════════════════════════════════════════════════════
   TEST SUITE 4 — Multiple monitor detection
═══════════════════════════════════════════════════════════════ */
describe('Multiple monitor detection', () => {
  beforeEach(() => fetch.mockClear());

  test('fires when availWidth > width * 1.05', () => {
    Object.defineProperty(window, 'screen', {
      value: { width: 1920, availWidth: 3840 },
      writable: true,
      configurable: true,
    });

    // Re-trigger the DOMContentLoaded handler logic directly
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);

    const multiMonCalls = fetch.mock.calls.filter(c => {
      try {
        const b = JSON.parse(c[1].body);
        return b.violation_type === 'multiple_monitor_suspected';
      } catch { return false; }
    });
    expect(multiMonCalls.length).toBeGreaterThanOrEqual(1);
  });

  test('does NOT fire on single monitor (availWidth == width)', () => {
    fetch.mockClear();
    Object.defineProperty(window, 'screen', {
      value: { width: 1920, availWidth: 1920 },
      writable: true,
      configurable: true,
    });
    document.dispatchEvent(new Event('DOMContentLoaded'));

    const multiMonCalls = fetch.mock.calls.filter(c => {
      try {
        const b = JSON.parse(c[1].body);
        return b.violation_type === 'multiple_monitor_suspected';
      } catch { return false; }
    });
    expect(multiMonCalls.length).toBe(0);
  });
});
