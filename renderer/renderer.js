const QUALITY_OPTIONS = [
  { key: "best", label: "Best Available (Auto, up to 8K)" },
  { key: "8k", label: "8K (4320p)" },
  { key: "4k", label: "4K (2160p)" },
  { key: "2k", label: "2K (1440p)" },
  { key: "1080p", label: "Full HD (1080p)" },
  { key: "720p", label: "HD (720p)" },
  { key: "480p", label: "SD (480p)" },
  { key: "360p", label: "Low (360p)" },
  { key: "audio", label: "Audio Only (MP3)" },
];

let state = {
  quality: "best",
  outputDir: "",
  playlist: false,
  subtitles: false,
  queue: [],
  recent: [],
  lastDownloadedPath: null,
  downloading: false,
};

const $ = (id) => document.getElementById(id);

// ---------- init ----------

async function init() {
  const settings = await window.nwgrabio.getSettings();
  state.quality = settings.quality || "best";
  state.outputDir = settings.outputDir || "";
  state.playlist = !!settings.playlist;
  state.subtitles = !!settings.subtitles;

  $("folder-input").value = state.outputDir;
  $("playlist-check").checked = state.playlist;
  $("subtitles-check").checked = state.subtitles;
  setQualityDisplay(state.quality);

  const version = await window.nwgrabio.getVersion();
  $("about-version").textContent = version;

  log("Ready. Paste a link above to get started.", "success");

  wireEvents();
  checkClipboard();
  setTimeout(checkForUpdates, 2000);
}

// ---------- logging & toast ----------

function log(text, cls) {
  const box = $("log-box");
  const line = document.createElement("div");
  line.className = "log-line" + (cls ? " " + cls : "");
  line.textContent = text;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function showToast(text, cls) {
  const toast = $("toast");
  toast.textContent = text;
  toast.className = "toast " + cls;
  toast.hidden = false;
  setTimeout(() => (toast.hidden = true), 4000);
}

// ---------- quality select2 ----------

function setQualityDisplay(key) {
  const opt = QUALITY_OPTIONS.find((o) => o.key === key) || QUALITY_OPTIONS[0];
  $("quality-value").textContent = opt.label;
}

function openQualityPopup() {
  closeQualityPopup();
  const container = $("quality-select");
  const popup = document.createElement("div");
  popup.className = "select2-popup";
  popup.id = "quality-popup";

  const search = document.createElement("input");
  search.className = "select2-search";
  search.placeholder = "Search quality...";
  popup.appendChild(search);

  const list = document.createElement("div");
  popup.appendChild(list);

  function renderOptions(filter) {
    list.innerHTML = "";
    const q = (filter || "").toLowerCase();
    const filtered = QUALITY_OPTIONS.filter((o) => o.label.toLowerCase().includes(q));
    if (filtered.length === 0) {
      const none = document.createElement("div");
      none.className = "select2-option";
      none.textContent = "No matches";
      list.appendChild(none);
      return;
    }
    filtered.forEach((o) => {
      const row = document.createElement("div");
      row.className = "select2-option";
      row.textContent = o.label;
      row.addEventListener("click", () => {
        state.quality = o.key;
        setQualityDisplay(o.key);
        window.nwgrabio.setSettings({ quality: o.key });
        closeQualityPopup();
      });
      list.appendChild(row);
    });
  }

  search.addEventListener("input", () => renderOptions(search.value));
  renderOptions("");

  container.appendChild(popup);
  search.focus();

  setTimeout(() => document.addEventListener("click", onDocClickCloseQuality), 0);
}

function onDocClickCloseQuality(e) {
  const popup = $("quality-popup");
  const field = $("quality-field");
  if (popup && !popup.contains(e.target) && !field.contains(e.target)) {
    closeQualityPopup();
  }
}

function closeQualityPopup() {
  const popup = $("quality-popup");
  if (popup) popup.remove();
  document.removeEventListener("click", onDocClickCloseQuality);
}

// ---------- clipboard / auto fetch ----------

let fetchTimer = null;

function looksLikeUrl(text) {
  return /^https?:\/\//i.test((text || "").trim());
}

async function checkClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    if (looksLikeUrl(text) && !$("url-input").value) {
      $("url-input").value = text;
    }
  } catch (e) {
    // clipboard read can be blocked until the window has focus; harmless
  }
}

function scheduleFetch() {
  if (fetchTimer) clearTimeout(fetchTimer);
  const url = $("url-input").value.trim();
  if (!looksLikeUrl(url)) return;
  fetchTimer = setTimeout(() => fetchInfo(url), 700);
}

async function fetchInfo(url) {
  $("preview-text").textContent = "Fetching video information...";
  $("preview-thumb").style.backgroundImage = "";
  try {
    const info = await window.nwgrabio.fetchInfo(url);
    let text = `${info.title}\nSource: ${info.uploader}`;
    if (info.duration) {
      const m = Math.floor(info.duration / 60);
      const s = Math.floor(info.duration % 60);
      text += `  |  Duration: ${m}m ${s}s`;
    }
    $("preview-text").textContent = text;
    if (info.thumbnail) {
      $("preview-thumb").style.backgroundImage = `url("${info.thumbnail}")`;
    }
    log("Video information loaded.", null);
  } catch (e) {
    $("preview-text").textContent = "Could not load video information. Check the link and try again.";
    log("Fetch info failed: " + e.message, "error");
  }
}

// ---------- queue ----------

function updateQueueHint() {
  const n = state.queue.length;
  $("queue-hint").textContent =
    n === 0
      ? "Paste a link, details load automatically."
      : `${n} link${n !== 1 ? "s" : ""} queued. Paste another and click + Queue, or click Download to start.`;
}

function refreshQueuePanel() {
  const panel = $("queue-panel");
  panel.innerHTML = "";
  if (state.queue.length === 0) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const maxVisible = 3;
  state.queue.slice(0, maxVisible).forEach((url, i) => {
    const row = document.createElement("div");
    row.className = "queue-item";
    const short = url.length > 50 ? url.slice(0, 47) + "..." : url;
    row.innerHTML = `<span class="queue-url">${short}</span><span class="queue-remove">&#10005;</span>`;
    row.querySelector(".queue-remove").addEventListener("click", () => {
      state.queue.splice(i, 1);
      updateQueueHint();
      refreshQueuePanel();
    });
    panel.appendChild(row);
  });
  const remaining = state.queue.length - maxVisible;
  if (remaining > 0) {
    const more = document.createElement("div");
    more.className = "queue-more";
    more.innerHTML = `<span>+${remaining} more queued</span><a>Clear all</a>`;
    more.querySelector("a").addEventListener("click", () => {
      state.queue = [];
      updateQueueHint();
      refreshQueuePanel();
    });
    panel.appendChild(more);
  }
}

function clearUrlField() {
  $("url-input").value = "";
  $("preview-text").textContent =
    "Paste a video or page link above. NWGrabio fetches details automatically, no extra clicks.";
  $("preview-thumb").style.backgroundImage = "";
}

// ---------- recent downloads ----------

function refreshRecentBox() {
  const box = $("recent-box");
  box.innerHTML = "";
  if (state.recent.length === 0) {
    box.innerHTML = '<div class="muted-note">Nothing yet.</div>';
    return;
  }
  state.recent.slice(0, 5).forEach((item) => {
    const row = document.createElement("div");
    row.className = "recent-item";
    const short = item.name.length > 34 ? item.name.slice(0, 31) + "..." : item.name;
    row.innerHTML = `<span class="name">${short}</span><span class="open-link">Open folder</span>`;
    row.querySelector(".open-link").addEventListener("click", () => {
      window.nwgrabio.openFolder(item.path);
    });
    box.appendChild(row);
  });
}

// ---------- download orchestration ----------

function setProgress(percent) {
  $("progress-fill").parentElement.classList.remove("indeterminate");
  $("progress-fill").style.width = Math.max(0, Math.min(100, percent)) + "%";
}

function setIndeterminate(on) {
  const track = $("progress-fill").parentElement;
  if (on) track.classList.add("indeterminate");
  else track.classList.remove("indeterminate");
}

function setButtonsDownloading(isDownloading) {
  $("download-btn").disabled = isDownloading;
  $("cancel-btn").disabled = !isDownloading;
}

async function startDownload() {
  const current = $("url-input").value.trim();
  const urls = [...state.queue];
  if (looksLikeUrl(current)) urls.push(current);

  if (urls.length === 0) {
    alert("Please enter a video or page URL first.");
    return;
  }
  if (state.downloading) return;

  state.queue = [];
  clearUrlField();
  updateQueueHint();
  refreshQueuePanel();

  state.downloading = true;
  setButtonsDownloading(true);
  $("open-folder-btn").disabled = true;
  setProgress(0);
  $("status-text").textContent = urls.length > 1 ? `Starting batch download of ${urls.length} links...` : "Starting download...";
  log(urls.length > 1 ? `Starting batch download of ${urls.length} links.` : `Starting download: ${urls[0]}`);

  let completed = 0;
  let failed = 0;

  window.nwgrabio.onProgress((data) => {
    setProgress(data.percent);
    let text = `Downloading  ${data.percent.toFixed(1)}%`;
    if (data.speed) text += `  |  ${data.speed}`;
    if (data.eta) text += `  |  ETA ${data.eta}`;
    $("status-text").textContent = text;
  });

  window.nwgrabio.onStatus((text) => {
    $("status-text").textContent = text;
    if (text.toLowerCase().includes("processing") || text.toLowerCase().includes("merging")) {
      setIndeterminate(true);
    }
  });

  for (let i = 0; i < urls.length; i++) {
    if (urls.length > 1) {
      $("status-text").textContent = `Item ${i + 1}/${urls.length}: starting...`;
    }
    setIndeterminate(false);
    const result = await window.nwgrabio.download({
      url: urls[i],
      quality: state.quality,
      outputDir: state.outputDir,
      playlist: state.playlist,
      subtitles: state.subtitles,
      wantsAudioOnly: state.quality === "audio",
    });

    setIndeterminate(false);

    if (result.cancelled) {
      log("Download cancelled by user.", "accent");
      break;
    }
    if (result.ok) {
      completed++;
      state.lastDownloadedPath = result.file || null;
      const name = result.file ? result.file.split(/[\\/]/).pop() : "Download";
      state.recent.unshift({ name, path: result.file, dir: state.outputDir });
      state.recent = state.recent.slice(0, 5);
      refreshRecentBox();
      log(`Saved: ${name}`, "success");
    } else {
      failed++;
      log(`An item in the queue failed: ${result.error}`, "error");
    }
  }

  state.downloading = false;
  setButtonsDownloading(false);
  setIndeterminate(false);
  setProgress(completed > 0 ? 100 : 0);

  if (completed > 0) $("open-folder-btn").disabled = false;

  let summary;
  if (failed === 0 && completed > 0) {
    summary = completed === 1 ? "Download complete" : `All ${completed} downloads complete`;
    $("status-text").textContent = summary;
    showToast(`${summary}. Click Open Folder to view your files.`, "success");
  } else if (completed > 0) {
    summary = `Finished: ${completed} succeeded, ${failed} failed`;
    $("status-text").textContent = summary;
    showToast(`${summary}. See the activity log for details.`, "error");
  } else if (failed > 0) {
    summary = "Download failed";
    $("status-text").textContent = summary;
    showToast("Download failed. See the activity log for details.", "error");
  } else {
    summary = "Cancelled";
    $("status-text").textContent = summary;
  }
}

// ---------- update check ----------

async function checkForUpdates(manual) {
  const result = await window.nwgrabio.checkForUpdates();
  if (!result || result.error) {
    if (manual) alert("Could not check for updates. Check your internet connection and try again.");
    return;
  }
  const current = result.current.split(".").map(Number);
  const latest = (result.latest || "").split(".").map(Number);
  const isNewer = latest.length && latest.some((v, i) => v > (current[i] || 0));
  if (isNewer) {
    if (confirm(`A new version of NWGrabio is available.\nYou have ${result.current}. The latest version is ${result.latest}.\n\nOpen the website to download it?`)) {
      window.nwgrabio.openExternal(result.websiteUrl);
    }
  } else if (manual) {
    alert(`You're up to date. NWGrabio ${result.current} is the latest version.`);
  }
}

// ---------- events ----------

function wireEvents() {
  $("url-input").addEventListener("input", scheduleFetch);
  $("url-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const url = $("url-input").value.trim();
      if (looksLikeUrl(url)) fetchInfo(url);
    }
  });

  $("paste-btn").addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      $("url-input").value = text.trim();
      scheduleFetch();
    } catch (e) {
      /* clipboard permission denied, ignore */
    }
  });

  $("clear-btn").addEventListener("click", clearUrlField);

  $("queue-btn").addEventListener("click", () => {
    const url = $("url-input").value.trim();
    if (!looksLikeUrl(url)) {
      alert("Paste a valid link first, then click + Queue.");
      return;
    }
    state.queue.push(url);
    clearUrlField();
    updateQueueHint();
    refreshQueuePanel();
  });

  $("quality-field").addEventListener("click", (e) => {
    e.stopPropagation();
    if ($("quality-popup")) closeQualityPopup();
    else openQualityPopup();
  });

  $("playlist-check").addEventListener("change", (e) => {
    state.playlist = e.target.checked;
    window.nwgrabio.setSettings({ playlist: state.playlist });
  });

  $("subtitles-check").addEventListener("change", (e) => {
    state.subtitles = e.target.checked;
    window.nwgrabio.setSettings({ subtitles: state.subtitles });
  });

  $("browse-btn").addEventListener("click", async () => {
    const folder = await window.nwgrabio.chooseFolder();
    if (folder) {
      state.outputDir = folder;
      $("folder-input").value = folder;
    }
  });

  $("download-btn").addEventListener("click", startDownload);

  $("cancel-btn").addEventListener("click", () => {
    window.nwgrabio.cancelDownload();
    $("status-text").textContent = "Cancelling...";
    log("Cancelling download... Partial files are kept, so downloading the same link again will resume.", "accent");
  });

  $("open-folder-btn").addEventListener("click", () => {
    window.nwgrabio.openFolder(state.lastDownloadedPath);
  });

  $("footer-website").addEventListener("click", (e) => {
    e.preventDefault();
    window.nwgrabio.openExternal("https://nethumwelikada.github.io/NWGrabio/");
  });
  $("footer-github").addEventListener("click", (e) => {
    e.preventDefault();
    window.nwgrabio.openExternal("https://github.com/NethumWelikada");
  });
  $("footer-about").addEventListener("click", (e) => {
    e.preventDefault();
    $("about-overlay").hidden = false;
  });
  $("about-close").addEventListener("click", () => ($("about-overlay").hidden = true));
  $("about-website").addEventListener("click", (e) => {
    e.preventDefault();
    window.nwgrabio.openExternal("https://nethumwelikada.github.io/NWGrabio/");
  });
  $("about-github").addEventListener("click", (e) => {
    e.preventDefault();
    window.nwgrabio.openExternal("https://github.com/NethumWelikada");
  });
}

init();
