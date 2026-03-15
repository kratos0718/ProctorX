const { app, BrowserWindow, shell, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let flaskProcess = null;
const PORT = 5050;

/* ── Start Flask backend ─────────────────────────── */
function startFlask() {
  // Resolve Python inside venv (packaged app uses resources/app/venv)
  const isPackaged = app.isPackaged;
  const appRoot = isPackaged
    ? path.join(process.resourcesPath, 'app')
    : path.join(__dirname, '..');

  const pythonExe = isPackaged
    ? path.join(appRoot, 'venv', 'Scripts', 'python.exe')   // Windows
    : path.join(appRoot, 'venv', 'Scripts', 'python.exe');

  const appPy = path.join(appRoot, 'app.py');

  flaskProcess = spawn(pythonExe, [appPy], {
    cwd: appRoot,
    env: { ...process.env, PORT: String(PORT), FLASK_ENV: 'production' },
  });

  flaskProcess.stdout.on('data', d => console.log('[Flask]', d.toString()));
  flaskProcess.stderr.on('data', d => console.error('[Flask]', d.toString()));
  flaskProcess.on('close', code => console.log('[Flask] exited', code));
}

/* ── Wait until Flask is ready ───────────────────── */
function waitForFlask(retries = 30, delay = 500) {
  return new Promise((resolve, reject) => {
    const check = () => {
      http.get(`http://127.0.0.1:${PORT}/`, res => {
        if (res.statusCode < 500) resolve();
        else retry();
      }).on('error', () => {
        if (retries-- > 0) setTimeout(check, delay);
        else reject(new Error('Flask did not start in time'));
      });
    };
    check();
  });
}

/* ── Create the Electron window ──────────────────── */
async function createWindow() {
  startFlask();

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#0C0A0D',
      symbolColor: '#F43F5E',
      height: 32,
    },
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    backgroundColor: '#0C0A0D',
    show: false,
    icon: path.join(__dirname, '..', 'static', 'icons', 'icon.png'),
  });

  // Show a loading screen while Flask starts
  mainWindow.loadURL('data:text/html,<html style="background:#0C0A0D;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:#F43F5E;font-size:22px">⟳ Starting ProctorX…</html>');
  mainWindow.show();

  try {
    await waitForFlask();
    mainWindow.loadURL(`http://127.0.0.1:${PORT}/`);
  } catch (err) {
    dialog.showErrorBox('ProctorX — Startup Error',
      'Could not start the Flask server.\n\n' + err.message);
    app.quit();
  }

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (flaskProcess) flaskProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('before-quit', () => {
  if (flaskProcess) flaskProcess.kill();
});
