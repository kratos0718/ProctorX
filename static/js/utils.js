/* UTILS.JS */

function showToast(msg, type='info') {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id='toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.className = 'show';
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 3500);
}

function getRiskColor(score) {
  if (score < 30) return 'var(--green)';
  if (score < 60) return 'var(--amber)';
  if (score < 80) return '#f97316';
  return 'var(--red)';
}
function getRiskLevel(score) {
  if (score < 30) return 'LOW';
  if (score < 60) return 'MEDIUM';
  if (score < 80) return 'HIGH';
  return 'CRITICAL';
}
function getRiskBadgeClass(score) {
  if (score < 30) return 'badge-green';
  if (score < 60) return 'badge-amber';
  if (score < 80) return 'badge-amber';
  return 'badge-red';
}
function nowStr() {
  return new Date().toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
}
function animateNum(el, target, dur=700) {
  const start = parseFloat(el.textContent)||0;
  const diff  = target - start;
  const t0    = performance.now();
  const step  = t => {
    const p = Math.min((t-t0)/dur, 1);
    const e = 1-Math.pow(1-p,3);
    el.textContent = (start+diff*e).toFixed(1);
    if (p<1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
