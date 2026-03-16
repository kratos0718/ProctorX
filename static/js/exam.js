/* ── EXAM.JS — ProctorX live exam controller ────────────── */
'use strict';

const TOTAL_TIME     = 45 * 60;
const FRAME_INTERVAL = 1000;

let timeLeft      = TOTAL_TIME;
let answers       = {};
let totalAnswered  = 0;
let tabSwitched   = false;
let stream        = null;
let lastFrameTs   = 0;
let busy          = false;
let violCount     = 0;
let currentQIdx   = 0;
let qCardIds      = [];

const socket = io();

/* ════════════════════════════════════════
   TIMER
════════════════════════════════════════ */
function tickTimer() {
  const m  = Math.floor(timeLeft / 60).toString().padStart(2, '0');
  const s  = (timeLeft % 60).toString().padStart(2, '0');
  const el = document.getElementById('timer');
  const bar = document.getElementById('time-bar');

  if (el) {
    el.textContent = `${m}:${s}`;
    el.classList.toggle('warning',  timeLeft <= 300 && timeLeft > 120);
    el.classList.toggle('critical', timeLeft <= 120);
  }
  if (bar) bar.style.width = (timeLeft / TOTAL_TIME * 100) + '%';
  if (timeLeft <= 0) { submitExam(); return; }
  timeLeft--;
}
setInterval(tickTimer, 1000);

/* ════════════════════════════════════════
   QUESTION INTERACTION
════════════════════════════════════════ */
function selectOption(qId, letter, el, evt) {
  /* ripple */
  if (evt && el) {
    const rect   = el.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    Object.assign(ripple.style, {
      left: (evt.clientX - rect.left - 20) + 'px',
      top:  (evt.clientY - rect.top  - 20) + 'px',
      width: '40px', height: '40px',
      position: 'absolute', borderRadius: '50%',
      background: 'rgba(244,63,94,.25)', transform: 'scale(0)',
      animation: 'rippleAnim .5s ease-out forwards', pointerEvents: 'none'
    });
    el.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
  }

  document.querySelectorAll('[data-qid="' + qId + '"]').forEach(o => o.classList.remove('selected'));
  if (el) el.classList.add('selected');

  if (!answers[qId]) {
    totalAnswered++;
    const card = document.getElementById('qcard-' + qId);
    if (card) card.classList.add('answered');
    const nb = document.getElementById('nav-' + qId);
    if (nb) nb.classList.add('answered');
  }
  answers[qId] = letter;
  refreshProgress();
}

function clearChoice(qId) {
  document.querySelectorAll('[data-qid="' + qId + '"]').forEach(o => o.classList.remove('selected'));
  if (answers[qId]) {
    delete answers[qId];
    totalAnswered--;
    const card = document.getElementById('qcard-' + qId);
    if (card) card.classList.remove('answered');
    const nb = document.getElementById('nav-' + qId);
    if (nb) nb.classList.remove('answered');
    refreshProgress();
  }
}

function refreshProgress() {
  const pct  = (totalAnswered / TOTAL_Q * 100).toFixed(0);
  const lbl  = document.getElementById('answered-label');
  const fill = document.getElementById('answered-fill');
  const prog = document.getElementById('prog-text');
  if (lbl)  lbl.textContent  = totalAnswered + ' / ' + TOTAL_Q + ' ANSWERED';
  if (fill) fill.style.width = pct + '%';
  if (prog) prog.textContent = totalAnswered + ' / ' + TOTAL_Q;
}

function jumpToQ(cardId) {
  const el = document.getElementById(cardId);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('focused');
  setTimeout(() => el.classList.remove('focused'), 1200);
}

/* Keyboard on focused question card */
function handleQKey(evt, qId) {
  const map = { '1': 'A', '2': 'B', '3': 'C', '4': 'D' };
  if (map[evt.key]) {
    const optEl = document.getElementById('opt-' + qId + '-' + map[evt.key]);
    if (optEl) selectOption(qId, map[evt.key], optEl, null);
    evt.preventDefault();
  }
}

/* Global keyboard nav */
document.addEventListener('keydown', function(evt) {
  /* block cheating */
  if (evt.ctrlKey && 'cvxaus'.includes(evt.key.toLowerCase())) { evt.preventDefault(); return; }
  if (evt.key === 'F12' || evt.key === 'PrintScreen') { evt.preventDefault(); return; }

  const tag = document.activeElement ? document.activeElement.tagName : '';
  if (tag === 'INPUT' || tag === 'TEXTAREA') return;

  if (evt.key === 'n' || evt.key === 'N') {
    currentQIdx = Math.min(currentQIdx + 1, qCardIds.length - 1);
    jumpToQ(qCardIds[currentQIdx]);
  }
  if (evt.key === 'p' || evt.key === 'P') {
    currentQIdx = Math.max(currentQIdx - 1, 0);
    jumpToQ(qCardIds[currentQIdx]);
  }
});

/* Intersection observer — highlight current nav button on scroll */
function setupScrollObserver() {
  const area = document.getElementById('questions-area');
  if (!area) return;
  const obs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        const rawId = e.target.id.replace('qcard-', '');
        const idx   = qCardIds.indexOf(e.target.id);
        if (idx >= 0) currentQIdx = idx;
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('current'));
        const nb = document.getElementById('nav-' + rawId);
        if (nb) nb.classList.add('current');
      }
    });
  }, { root: area, threshold: 0.4 });

  document.querySelectorAll('.q-card').forEach(c => obs.observe(c));
}

/* ════════════════════════════════════════
   CAMERA — handles HTTP/insecure context
════════════════════════════════════════ */
async function startCam() {
  hideCamError();
  setCamStatus('⬤ REQUESTING…', '');

  /* mediaDevices is undefined on non-localhost HTTP */
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showCamError(
      '🔒',
      'Insecure Context',
      'Camera requires HTTPS or localhost.<br>Open the exam at <b>http://localhost:5050</b> instead of the network IP.'
    );
    setCamStatus('⬤ UNAVAILABLE', 'err');
    setTrk('trk-cam', 'err', 'HTTP');
    addViol('high', '🔒', 'Camera unavailable — insecure context (use localhost)');
    return;
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 320 }, height: { ideal: 240 },
               facingMode: 'user', frameRate: { ideal: 15 } },
      audio: false
    });

    const v = document.getElementById('webcam');
    v.srcObject = stream;
    await new Promise(function(res, rej) { v.onloadedmetadata = res; v.onerror = rej; });
    await v.play();

    setCamStatus('⬤ ACTIVE', 'active');
    setTrk('trk-cam', 'ok', 'ON');
    hideCamError();
    requestAnimationFrame(frameLoop);

  } catch (err) {
    console.warn('[CAM]', err.name, err.message);
    var msgs = {
      NotAllowedError:      ['🚫', 'Permission Denied',  'Click the camera icon in your browser bar, allow access, then click Retry.'],
      PermissionDeniedError:['🚫', 'Permission Denied',  'Camera permission was blocked. Allow it in browser settings and retry.'],
      NotFoundError:        ['🔌', 'No Camera Found',    'No webcam detected. Please connect a camera and retry.'],
      DevicesNotFoundError: ['🔌', 'No Camera Found',    'No webcam detected. Please connect a camera and retry.'],
      NotReadableError:     ['⚠️', 'Camera In Use',     'Another app is using the camera. Close it and retry.'],
    };
    var m = msgs[err.name] || ['⚠️', 'Camera Error', err.name + ': ' + err.message];
    showCamError(m[0], m[1], m[2]);
    setCamStatus('⬤ ERROR', 'err');
    setTrk('trk-cam', 'err', 'DENIED');
    addViol('high', '🚫', 'Webcam access denied');
  }
}

function showCamError(icon, title, msg) {
  var el = document.getElementById('cam-error');
  if (!el) return;
  var i = document.getElementById('cem-icon');
  var t = document.getElementById('cem-title');
  var m = document.getElementById('cem-msg');
  if (i) i.textContent  = icon;
  if (t) t.textContent  = title;
  if (m) m.innerHTML    = msg;
  el.classList.add('show');
}

function hideCamError() {
  var el = document.getElementById('cam-error');
  if (el) el.classList.remove('show');
}

function setCamStatus(text, cls) {
  var el = document.getElementById('cam-status-bar');
  if (!el) return;
  el.textContent = text;
  el.className   = cls || '';
  el.id          = 'cam-status-bar';
}

/* ════════════════════════════════════════
   FRAME CAPTURE + PROCTOR API
════════════════════════════════════════ */
function snap() {
  var v = document.getElementById('webcam');
  if (!v || !v.videoWidth) return null;
  var c = document.createElement('canvas');
  c.width = 320; c.height = 240;
  c.getContext('2d').drawImage(v, 0, 0, 320, 240);
  return c.toDataURL('image/jpeg', 0.55);
}

async function frameLoop(ts) {
  if (!stream || !stream.active) return;
  if (ts - lastFrameTs >= FRAME_INTERVAL && !busy) {
    lastFrameTs = ts;
    busy = true;
    await sendFrame();
    busy = false;
  }
  requestAnimationFrame(frameLoop);
}

async function sendFrame() {
  var frame = snap();
  if (!frame) return;
  try {
    var res = await fetch('/proctor/frame/' + SESSION_ID, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frame: frame, tab_switch: tabSwitched })
    });
    tabSwitched = false;
    if (!res.ok) return;
    var d = await res.json();
    if (d.error) return;
    updateRisk(d);
    if (d.stats)  updateStats(d.stats);
    if (d.alerts) {
      var icons = { high: '🚨', medium: '⚠️', low: 'ℹ️' };
      d.alerts.forEach(function(a) { addViol(a.severity, icons[a.severity] || '⚠️', a.msg); });
    }
  } catch (_) { /* silent */ }
}

/* ════════════════════════════════════════
   RISK + TRACKING UI
════════════════════════════════════════ */
function updateRisk(d) {
  var score = parseFloat(d.risk_score) || 0;
  var color = getRiskColor(score);
  var level = getRiskLevel(score);

  var numEl = document.getElementById('risk-num');
  if (numEl) { animateNum(numEl, score); numEl.style.color = color; }

  var fill = document.getElementById('risk-fill');
  if (fill) { fill.style.width = score + '%'; fill.style.background = color; }

  var badge = document.getElementById('risk-badge');
  if (badge) {
    badge.textContent = level;
    var cls = { LOW: 'low', MEDIUM: 'med', HIGH: 'high', CRITICAL: 'crit' };
    badge.className = cls[level] || 'low';
  }
}

function updateStats(s) {
  if (!s) return;

  var camOk = stream && stream.active;
  setTrk('trk-cam',  camOk ? 'ok' : 'err',  camOk ? 'ON' : 'OFF');

  var fc = s.face_count != null ? s.face_count : 0;
  if      (fc === 1) setTrk('trk-face', 'ok',   '1 face');
  else if (fc > 1)   setTrk('trk-face', 'warn', fc + ' faces');
  else               setTrk('trk-face', 'err',  'none');

  var g = s.gaze || 'unknown';
  if      (g === 'center')  setTrk('trk-eye', 'ok',   'center');
  else if (g === 'unknown') setTrk('trk-eye', 'err',  '—');
  else                      setTrk('trk-eye', 'warn', g);

  var h = s.head || 'forward';
  if      (h === 'forward') setTrk('trk-head', 'ok',   'fwd');
  else if (h === 'unknown') setTrk('trk-head', 'err',  '—');
  else                      setTrk('trk-head', 'warn', h);

  setTrk('trk-audio', s.talking ? 'err' : 'ok', s.talking ? 'talking' : 'quiet');
}

function setTrk(dotId, state, valText) {
  var dot = document.getElementById(dotId);
  if (dot) dot.className = 'trk-dot ' + state;
  var valId = 'val-' + dotId.replace('trk-', '');
  var val   = document.getElementById(valId);
  if (val)  val.textContent = valText || '—';
}

/* ════════════════════════════════════════
   VIOLATIONS FEED
════════════════════════════════════════ */
function addViol(sev, icon, msg) {
  var feed = document.getElementById('viols-feed');
  if (!feed) return;
  var empty = feed.querySelector('.vf-empty');
  if (empty) empty.remove();

  violCount++;
  var cnt = document.getElementById('viol-count');
  if (cnt) cnt.textContent = violCount;

  var div = document.createElement('div');
  div.className = 'viol-item ' + sev;
  div.innerHTML =
    '<span class="vi-icon">' + icon + '</span>' +
    '<div><div class="vi-msg">' + msg + '</div>' +
    '<div class="vi-time">' + nowStr() + '</div></div>';
  feed.prepend(div);
  if (feed.children.length > 60) feed.lastChild.remove();
}

/* ════════════════════════════════════════
   FULLSCREEN LOCK
════════════════════════════════════════ */
var _fsWarned = false;
var _fsViolCount = 0;

function enterFullscreen() {
  var el = document.documentElement;
  var fn = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen;
  if (fn) fn.call(el).catch(function() { /* user denied — handled by event */ });
}

function exitFullscreenFn() {
  return document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
}

function isFullscreen() {
  return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
}

/* Overlay shown when student exits fullscreen */
function showFsWarning() {
  var ov = document.getElementById('fs-overlay');
  if (ov) ov.classList.add('show');
}
function hideFsWarning() {
  var ov = document.getElementById('fs-overlay');
  if (ov) ov.classList.remove('show');
}

document.addEventListener('fullscreenchange',     _onFsChange);
document.addEventListener('webkitfullscreenchange', _onFsChange);
document.addEventListener('mozfullscreenchange',  _onFsChange);
document.addEventListener('MSFullscreenChange',   _onFsChange);

function _onFsChange() {
  if (!isFullscreen()) {
    _fsViolCount++;
    addViol('high', '⛶', 'Fullscreen exited — violation #' + _fsViolCount);
    sendBrowserViolation('fullscreen_exit',
      'Student exited fullscreen (event #' + _fsViolCount + ')');
    showFsWarning();
  } else {
    hideFsWarning();
  }
}

/* Re-enter fullscreen button (inside overlay) */
function reEnterFs() {
  hideFsWarning();
  enterFullscreen();
}

/* ════════════════════════════════════════
   TAB / VISIBILITY
════════════════════════════════════════ */
document.addEventListener('visibilitychange', function() {
  if (document.hidden) {
    tabSwitched = true;
    var w = document.getElementById('tab-warning');
    if (w) { w.classList.add('show'); setTimeout(function() { w.classList.remove('show'); }, 4000); }
    addViol('high', '🚨', 'Tab switch detected!');
    /* also feed into browser detection tracker */
    _trackFocusLoss('window_focus_lost', 'Tab hidden / window switched');
  }
});
window.addEventListener('blur', function() { tabSwitched = true; });
document.addEventListener('contextmenu', function(e) { e.preventDefault(); });

/* ════════════════════════════════════════
   BROWSER ANTI-CHEAT DETECTION
════════════════════════════════════════ */

/* Send a browser-detected violation to the backend */
function sendBrowserViolation(type, details) {
  if (typeof SESSION_ID === 'undefined') return;
  fetch('/browser/violation/' + SESSION_ID, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      violation_type: type,
      timestamp: new Date().toISOString(),
      details: details
    })
  }).catch(function() { /* silent — offline or insecure context */ });
}

/* ── Clipboard access ─────────────────────── */
document.addEventListener('copy',  function() {
  sendBrowserViolation('clipboard_access', 'Copy attempt (Ctrl+C / Cmd+C)');
  addViol('high', '📋', 'Clipboard copy detected');
});
document.addEventListener('cut', function() {
  sendBrowserViolation('clipboard_access', 'Cut attempt (Ctrl+X / Cmd+X)');
  addViol('high', '📋', 'Clipboard cut detected');
});
document.addEventListener('paste', function() {
  sendBrowserViolation('clipboard_access', 'Paste attempt (Ctrl+V / Cmd+V)');
  addViol('high', '📋', 'Clipboard paste detected');
});

/* ── Focus loss + rapid tab-switch tracking ── */
var _focusLossTimes = [];
function _trackFocusLoss(type, details) {
  var now = Date.now();
  _focusLossTimes.push(now);
  /* keep only events within the last 30 seconds */
  _focusLossTimes = _focusLossTimes.filter(function(t) { return now - t < 30000; });

  if (_focusLossTimes.length >= 3) {
    /* 3+ focus losses in 30 s → rapid_tab_switch */
    sendBrowserViolation('rapid_tab_switch',
      'Rapid focus loss: ' + _focusLossTimes.length + ' events in 30 s');
    addViol('high', '⚡', 'Rapid tab switching detected (' + _focusLossTimes.length + 'x)');
    _focusLossTimes = []; /* reset after reporting */
  } else {
    sendBrowserViolation(type, details);
  }
}

/* ── Multiple monitor detection (run once on load) ── */
document.addEventListener('DOMContentLoaded', function() {
  if (window.screen && window.screen.availWidth > window.screen.width * 1.05) {
    sendBrowserViolation('multiple_monitor_suspected',
      'Multiple monitors suspected — screen: ' + window.screen.width +
      'px, availWidth: ' + window.screen.availWidth + 'px');
    addViol('medium', '🖥️',
      'Multiple monitors suspected (' + window.screen.availWidth + 'px available)');
  }
  /* Auto-enter fullscreen when exam loads */
  enterFullscreen();
});

/* ════════════════════════════════════════
   SUBMIT
════════════════════════════════════════ */
async function submitExam() {
  if (!confirm('Submit exam? This cannot be undone.')) return;
  var btn = document.getElementById('submit-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Submitting…'; }
  if (stream) stream.getTracks().forEach(function(t) { t.stop(); });
  try {
    var res  = await fetch('/exam/' + SESSION_ID + '/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers: answers })
    });
    var data = await res.json();
    if (data.redirect) window.location.href = data.redirect;
  } catch (_) {
    if (btn) { btn.disabled = false; btn.textContent = 'Submit Exam →'; }
    showToast('Submission failed — please try again');
  }
}

/* ════════════════════════════════════════
   SOCKETIO
════════════════════════════════════════ */
socket.on('session_terminated', function(d) {
  if (d.session_id === SESSION_ID) {
    if (stream) stream.getTracks().forEach(function(t) { t.stop(); });
    var ov = document.getElementById('terminated-overlay');
    if (ov) ov.classList.add('show');
  }
});

/* ════════════════════════════════════════
   INIT
════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.q-card').forEach(function(c) { qCardIds.push(c.id); });
  setupScrollObserver();
  startCam();
});
