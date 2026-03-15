/**
 * Vortex — Vanilla JS canvas animation
 * Ported from the React/framer-motion version.
 * Requires simplex-noise v2 loaded before this file.
 */
(function (global) {
  'use strict';

  class Vortex {
    constructor(canvas, opts) {
      opts = opts || {};
      this.canvas = canvas;
      this.ctx    = canvas.getContext('2d');

      this.particleCount      = opts.particleCount || 700;
      this.particlePropCount  = 9;
      this.particlePropsLen   = this.particleCount * this.particlePropCount;
      this.rangeY             = opts.rangeY        || 100;
      this.baseTTL            = 50;
      this.rangeTTL           = 150;
      this.baseSpeed          = opts.baseSpeed     || 0.0;
      this.rangeSpeed         = opts.rangeSpeed    || 1.5;
      this.baseRadius         = opts.baseRadius    || 1;
      this.rangeRadius        = opts.rangeRadius   || 2;
      this.baseHue            = opts.baseHue       || 220;
      this.rangeHue           = 100;
      this.noiseSteps         = 3;
      this.xOff               = 0.00125;
      this.yOff               = 0.00125;
      this.zOff               = 0.0005;
      this.backgroundColor    = opts.backgroundColor || 'rgba(0,0,0,0)';

      this.tick           = 0;
      this.particleProps  = new Float32Array(this.particlePropsLen);
      this.center         = [0, 0];
      this.TAU            = 2 * Math.PI;
      this._rafId         = null;
      this._running       = false;

      /* simplex-noise v2 → new SimplexNoise() */
      this.noise = new SimplexNoise();

      this._onResize = this._handleResize.bind(this);
      window.addEventListener('resize', this._onResize);

      this._resize();
      this._initParticles();
      this.start();
    }

    /* ── public ─────────────────────────────────────────── */
    start() {
      if (this._running) return;
      this._running = true;
      this._draw();
    }

    stop() {
      this._running = false;
      if (this._rafId) { cancelAnimationFrame(this._rafId); this._rafId = null; }
    }

    destroy() {
      this.stop();
      window.removeEventListener('resize', this._onResize);
    }

    /* ── private ─────────────────────────────────────────── */
    _rand(n)        { return n * Math.random(); }
    _randRange(n)   { return n - this._rand(2 * n); }
    _lerp(a, b, t)  { return (1 - t) * a + t * b; }
    _fadeInOut(t, m){ const hm = 0.5 * m; return Math.abs(((t + hm) % m) - hm) / hm; }

    _handleResize() {
      this._resize();
      // re-center all particles
      this._initParticles();
    }

    _resize() {
      const p = this.canvas.parentElement;
      const w = p ? p.offsetWidth  : window.innerWidth;
      const h = p ? p.offsetHeight : window.innerHeight;
      this.canvas.width  = w;
      this.canvas.height = h;
      this.center[0] = w * 0.5;
      this.center[1] = h * 0.5;
    }

    _initParticles() {
      this.tick = 0;
      this.particleProps = new Float32Array(this.particlePropsLen);
      for (let i = 0; i < this.particlePropsLen; i += this.particlePropCount) {
        this._initParticle(i);
      }
    }

    _initParticle(i) {
      const x      = this._rand(this.canvas.width);
      const y      = this.center[1] + this._randRange(this.rangeY);
      const vx     = 0, vy = 0, life = 0;
      const ttl    = this.baseTTL   + this._rand(this.rangeTTL);
      const speed  = this.baseSpeed  + this._rand(this.rangeSpeed);
      const radius = this.baseRadius + this._rand(this.rangeRadius);
      const hue    = this.baseHue    + this._rand(this.rangeHue);
      this.particleProps.set([x, y, vx, vy, life, ttl, speed, radius, hue], i);
    }

    _draw() {
      if (!this._running) return;
      this.tick++;

      const ctx    = this.ctx;
      const canvas = this.canvas;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = this.backgroundColor;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      this._drawParticles();
      this._renderGlow();
      this._renderToScreen();

      this._rafId = requestAnimationFrame(() => this._draw());
    }

    _drawParticles() {
      for (let i = 0; i < this.particlePropsLen; i += this.particlePropCount) {
        this._updateParticle(i);
      }
    }

    _updateParticle(i) {
      const p = this.particleProps;
      const i2=i+1,i3=i+2,i4=i+3,i5=i+4,i6=i+5,i7=i+6,i8=i+7,i9=i+8;

      const x  = p[i], y = p[i2];
      const n  = this.noise.noise3D(x * this.xOff, y * this.yOff, this.tick * this.zOff)
                   * this.noiseSteps * this.TAU;
      const vx = this._lerp(p[i3], Math.cos(n), 0.5);
      const vy = this._lerp(p[i4], Math.sin(n), 0.5);
      const life = p[i5], ttl = p[i6], speed = p[i7];
      const x2 = x + vx * speed, y2 = y + vy * speed;
      const radius = p[i8], hue = p[i9];

      this._drawParticle(x, y, x2, y2, life, ttl, radius, hue);

      p[i]=x2; p[i2]=y2; p[i3]=vx; p[i4]=vy; p[i5]=life+1;
      if (this._outOfBounds(x, y) || life > ttl) this._initParticle(i);
    }

    _drawParticle(x, y, x2, y2, life, ttl, radius, hue) {
      const ctx = this.ctx;
      ctx.save();
      ctx.lineCap       = 'round';
      ctx.lineWidth     = radius;
      ctx.strokeStyle   = `hsla(${hue},100%,60%,${this._fadeInOut(life, ttl)})`;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      ctx.restore();
    }

    _outOfBounds(x, y) {
      return x > this.canvas.width || x < 0 || y > this.canvas.height || y < 0;
    }

    _renderGlow() {
      const ctx = this.ctx, c = this.canvas;
      ctx.save(); ctx.filter='blur(8px) brightness(200%)'; ctx.globalCompositeOperation='lighter'; ctx.drawImage(c,0,0); ctx.restore();
      ctx.save(); ctx.filter='blur(4px) brightness(200%)'; ctx.globalCompositeOperation='lighter'; ctx.drawImage(c,0,0); ctx.restore();
    }

    _renderToScreen() {
      const ctx = this.ctx, c = this.canvas;
      ctx.save(); ctx.globalCompositeOperation='lighter'; ctx.drawImage(c,0,0); ctx.restore();
    }
  }

  /* ── factory helper ──────────────────────────────────── */
  /**
   * mountVortex(containerId, options)
   * Injects a <canvas> into the given container and starts the animation.
   * The container should be position:relative / absolute.
   * Returns the Vortex instance.
   */
  global.mountVortex = function (containerId, options) {
    const container = document.getElementById(containerId);
    if (!container) return null;
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;';
    container.style.position = container.style.position || 'relative';
    container.insertBefore(canvas, container.firstChild);
    return new Vortex(canvas, options);
  };

  global.Vortex = Vortex;
})(window);
