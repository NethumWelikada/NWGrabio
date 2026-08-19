// NWGrabio - Electron main process
// Grab Anything, From Anywhere.
// Developed by Nethum Welikada
// Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada

const { app, BrowserWindow, Tray, Menu, ipcMain, dialog, shell, nativeImage } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");
const { spawn } = require("child_process");
const https = require("https");
const Store = require("electron-store");

const APP_NAME = "NWGrabio";
const APP_TAGLINE = "Grab Anything, From Anywhere.";
const APP_VERSION = require("../package.json").version;
const GITHUB_REPO = "NethumWelikada/NWGrabio";
const WEBSITE_URL = "https://nethumwelikada.github.io/NWGrabio/";

const store = new Store({
  defaults: {
    quality: "best",
    outputDir: path.join(os.homedir(), "Downloads"),
    playlist: false,
    subtitles: false,
  },
});

let mainWindow = null;
let tray = null;
let isQuitting = false;
let activeDownloadProcess = null;
let cancelRequested = false;

// ---------- binary resolution ----------
// In development, yt-dlp.exe / ffmpeg.exe are expected in ./bin.
// In a packaged build, electron-builder copies extraResources into the
// app's resources/bin folder alongside the installed exe.

function getBinPath(name) {
  const fromResources = app.isPackaged
    ? path.join(process.resourcesPath, "bin", name)
    : path.join(__dirname, "..", "bin", name);
  return fromResources;
}

function getYtDlpPath() {
  return getBinPath(process.platform === "win32" ? "yt-dlp.exe" : "yt-dlp");
}

function getFfmpegPath() {
  return getBinPath(process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg");
}

// ---------- window ----------

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 720,
    minWidth: 820,
    minHeight: 640,
    backgroundColor: "#1E1E1E",
    icon: path.join(__dirname, "..", "assets", "icon.png"),
    title: `${APP_NAME} | ${APP_TAGLINE}`,
    titleBarStyle: "hidden",
    titleBarOverlay: {
      color: "#252526",
      symbolColor: "#D4D4D4",
      height: 37,
    },
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, "..", "renderer", "index.html"));

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      if (tray) {
        tray.displayBalloon &&
          tray.displayBalloon({
            title: APP_NAME,
            content: "NWGrabio is still running in the system tray.",
          });
      }
    }
  });
}

function createTray() {
  const trayImage = nativeImage.createFromPath(path.join(__dirname, "..", "assets", "tray-icon.png"));
  tray = new Tray(trayImage);
  tray.setToolTip(APP_NAME);

  const menu = Menu.buildFromTemplate([
    {
      label: "Show NWGrabio",
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      },
    },
    { type: "separator" },
    {
      label: "Exit",
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(menu);
  tray.on("click", () => {
    mainWindow.show();
    mainWindow.focus();
  });
}

function notify(title, body) {
  if (tray && tray.displayBalloon) {
    try {
      tray.displayBalloon({ title, content: body });
    } catch (e) {
      // ignore, non-Windows platforms don't support balloons
    }
  }
}

app.whenReady().then(() => {
  // No native File/Edit/View/Window menu bar: it renders with the OS's
  // default white styling regardless of our CSS, since it's outside the
  // web page entirely. The app's own dark custom title bar replaces it.
  Menu.setApplicationMenu(null);
  createWindow();
  createTray();
});

app.on("window-all-closed", () => {
  // Intentionally do nothing: the app lives in the tray until Exit is
  // chosen explicitly, matching the desktop app's existing behavior.
});

app.on("before-quit", () => {
  isQuitting = true;
});

// ---------- IPC: settings ----------

ipcMain.handle("settings:get", () => {
  return store.store;
});

ipcMain.handle("settings:set", (event, partial) => {
  for (const [key, value] of Object.entries(partial)) {
    store.set(key, value);
  }
  return store.store;
});

ipcMain.handle("dialog:chooseFolder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    defaultPath: store.get("outputDir"),
    properties: ["openDirectory"],
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  const folder = result.filePaths[0];
  store.set("outputDir", folder);
  return folder;
});

ipcMain.handle("shell:openFolder", (event, filePath) => {
  if (filePath && fs.existsSync(filePath)) {
    shell.showItemInFolder(filePath);
  } else {
    const dir = store.get("outputDir");
    if (dir && fs.existsSync(dir)) shell.openPath(dir);
  }
});

ipcMain.handle("shell:openExternal", (event, url) => {
  shell.openExternal(url);
});

ipcMain.handle("app:getVersion", () => APP_VERSION);

// ---------- IPC: clipboard read is done in renderer via navigator.clipboard ----------

// ---------- yt-dlp: fetch info ----------

ipcMain.handle("ytdlp:fetchInfo", async (event, url) => {
  return new Promise((resolve, reject) => {
    const ytDlpPath = getYtDlpPath();
    if (!fs.existsSync(ytDlpPath)) {
      reject(new Error("The download engine is missing from this build. Please reinstall NWGrabio."));
      return;
    }

    const args = ["-j", "--no-warnings", "--skip-download", "--no-playlist", url];
    const proc = spawn(ytDlpPath, args);
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));

    proc.on("close", (code) => {
      if (code !== 0 || !stdout.trim()) {
        reject(new Error(stderr.trim() || "Could not load video information."));
        return;
      }
      try {
        const info = JSON.parse(stdout.trim().split("\n")[0]);
        resolve({
          title: info.title || "Unknown title",
          uploader: info.uploader || "Unknown source",
          duration: info.duration || null,
          thumbnail: info.thumbnail || null,
        });
      } catch (e) {
        reject(new Error("Could not parse video information."));
      }
    });

    proc.on("error", (err) => reject(err));
  });
});

// ---------- yt-dlp: download (single item, called in a loop by renderer for batches) ----------

const QUALITY_FORMATS = {
  best: "bestvideo+bestaudio/best",
  "8k": "bestvideo[height<=4320]+bestaudio/best",
  "4k": "bestvideo[height<=2160]+bestaudio/best",
  "2k": "bestvideo[height<=1440]+bestaudio/best",
  "1080p": "bestvideo[height<=1080]+bestaudio/best",
  "720p": "bestvideo[height<=720]+bestaudio/best",
  "480p": "bestvideo[height<=480]+bestaudio/best",
  "360p": "bestvideo[height<=360]+bestaudio/best",
  audio: "bestaudio/best",
};

ipcMain.handle("ytdlp:cancel", () => {
  cancelRequested = true;
  if (activeDownloadProcess) {
    try {
      activeDownloadProcess.kill();
    } catch (e) {
      /* ignore */
    }
  }
  return true;
});

ipcMain.handle("ytdlp:download", async (event, { url, quality, outputDir, playlist, subtitles, wantsAudioOnly }) => {
  cancelRequested = false;
  const ytDlpPath = getYtDlpPath();
  const ffmpegPath = getFfmpegPath();

  if (!fs.existsSync(ytDlpPath)) {
    return { ok: false, error: "The download engine is missing from this build. Please reinstall NWGrabio." };
  }

  const format = QUALITY_FORMATS[quality] || QUALITY_FORMATS.best;
  const outTemplate = path.join(outputDir, "%(title)s.%(ext)s");

  function buildArgs(includeSubtitles) {
    const a = ["--newline", "--no-warnings", "-f", format, "-o", outTemplate, "--continue"];
    if (fs.existsSync(ffmpegPath)) a.push("--ffmpeg-location", ffmpegPath);
    if (!wantsAudioOnly) {
      a.push("--merge-output-format", "mp4");
    } else {
      a.push("-x", "--audio-format", "mp3", "--audio-quality", "192K");
    }
    if (!playlist) a.push("--no-playlist");
    if (includeSubtitles && subtitles) {
      a.push("--write-sub", "--write-auto-sub", "--sub-lang", "en", "--sub-format", "srt", "--sleep-subtitles", "1");
    }
    a.push(url);
    return a;
  }

  return new Promise((resolve) => {
    const runOnce = (args, allowSubtitleFallback) => {
      const proc = spawn(ytDlpPath, args);
      activeDownloadProcess = proc;
      let lastFile = null;
      let stderrBuf = "";

      proc.stdout.on("data", (data) => {
        const text = data.toString();
        text.split("\n").forEach((line) => {
          line = line.trim();
          if (!line) return;

          const pctMatch = line.match(/\[download\]\s+([\d.]+)%/);
          if (pctMatch) {
            const speedMatch = line.match(/at\s+([\d.]+\w+\/s)/);
            const etaMatch = line.match(/ETA\s+([\d:]+)/);
            event.sender.send("ytdlp:progress", {
              percent: parseFloat(pctMatch[1]),
              speed: speedMatch ? speedMatch[1] : null,
              eta: etaMatch ? etaMatch[1] : null,
            });
          } else if (line.includes("Destination:")) {
            lastFile = line.split("Destination:")[1].trim();
          } else if (line.startsWith("[Merger]") || line.startsWith("[ExtractAudio]")) {
            const m = line.match(/Merging formats into "(.+)"/) || line.match(/Destination:\s*(.+)/);
            if (m) lastFile = m[1].trim().replace(/^"|"$/g, "");
            event.sender.send("ytdlp:status", "Processing / merging streams...");
          }
        });
      });

      proc.stderr.on("data", (data) => {
        stderrBuf += data.toString();
      });

      proc.on("close", (code) => {
        activeDownloadProcess = null;
        if (cancelRequested) {
          resolve({ ok: false, cancelled: true });
          return;
        }
        if (code === 0) {
          resolve({ ok: true, file: lastFile });
          return;
        }
        if (allowSubtitleFallback && subtitles && /subtitle/i.test(stderrBuf)) {
          event.sender.send("ytdlp:status", "Subtitles unavailable right now, downloading video without them...");
          runOnce(buildArgs(false), false);
          return;
        }
        resolve({ ok: false, error: stderrBuf.trim() || `yt-dlp exited with code ${code}` });
      });

      proc.on("error", (err) => {
        activeDownloadProcess = null;
        resolve({ ok: false, error: err.message });
      });
    };

    runOnce(buildArgs(true), true);
  });
});

// ---------- update check ----------

function httpsGetJson(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { "User-Agent": "NWGrabio" } }, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            resolve(JSON.parse(data));
          } catch (e) {
            reject(e);
          }
        });
      })
      .on("error", reject);
  });
}

ipcMain.handle("update:check", async () => {
  try {
    const data = await httpsGetJson(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`);
    const latestTag = (data.tag_name || "").replace(/^v/i, "");
    return { latest: latestTag, current: APP_VERSION, websiteUrl: WEBSITE_URL };
  } catch (e) {
    return { error: true };
  }
});
