# ProctorX Deployment Guide

## 1 — Web App (Railway — recommended)

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Create project: `railway init`
4. Deploy: `railway up`
5. Add env variable in Railway dashboard:
   - `SECRET_KEY` → any 64-char random string
6. Your app is live at the Railway URL.

> **Note:** Camera-based proctoring (mediapipe/opencv) requires a VM plan,
> not the free tier. The coding exam and analytics work on any tier.

---

## 2 — Web App (Render — alternative)

1. Push your code to GitHub
2. Go to render.com → New Web Service
3. Connect your repo
4. Render reads `render.yaml` automatically and sets everything up
5. Add `SECRET_KEY` in Environment settings

---

## 3 — Windows App (Electron)

```bash
npm install          # installs electron + electron-builder
npm run build-win    # creates installer in dist-electron/
```

The NSIS installer packages Python, Flask, and the full app into a single .exe.

---

## 4 — Progressive Web App (Android + iOS — no app store needed)

PWA works automatically once deployed to Railway/Render.

**Android:** Open the site in Chrome → 3-dot menu → "Add to Home Screen"
**iOS:** Open in Safari → Share → "Add to Home Screen"

The app installs like a native app, works fullscreen, and has a ProctorX icon.

---

## 5 — Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random 64-char string (required in production) |
| `DATABASE_URL` | Leave as sqlite for local, set postgres URL for cloud |
| `PORT` | Default 5050 |
