// Minimal preload — context bridge for any future IPC needs
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('proctorx', {
  platform: process.platform,
  version: process.versions.electron,
});
