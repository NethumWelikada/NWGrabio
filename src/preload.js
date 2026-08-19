const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("nwgrabio", {
  getSettings: () => ipcRenderer.invoke("settings:get"),
  setSettings: (partial) => ipcRenderer.invoke("settings:set", partial),
  chooseFolder: () => ipcRenderer.invoke("dialog:chooseFolder"),
  openFolder: (filePath) => ipcRenderer.invoke("shell:openFolder", filePath),
  openExternal: (url) => ipcRenderer.invoke("shell:openExternal", url),
  getVersion: () => ipcRenderer.invoke("app:getVersion"),

  fetchInfo: (url) => ipcRenderer.invoke("ytdlp:fetchInfo", url),
  download: (payload) => ipcRenderer.invoke("ytdlp:download", payload),
  cancelDownload: () => ipcRenderer.invoke("ytdlp:cancel"),
  onProgress: (callback) => ipcRenderer.on("ytdlp:progress", (event, data) => callback(data)),
  onStatus: (callback) => ipcRenderer.on("ytdlp:status", (event, text) => callback(text)),

  checkForUpdates: () => ipcRenderer.invoke("update:check"),
});
