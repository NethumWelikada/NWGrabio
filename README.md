# NWGrabio (Electron)

A ground-up rewrite of NWGrabio using Electron, aiming for the kind of modern,
polished dark UI seen in apps like VS Code, rather than the native OS widget
look of the original Tkinter/Python version.

## What changed from the Python version

- **UI**: HTML/CSS/JavaScript instead of Tkinter. VS Code-style dark theme
  (`#1E1E1E` backgrounds, `#007ACC` accent blue, Segoe UI / Consolas fonts).
- **Download engine**: still yt-dlp, but invoked as a standalone `.exe`
  subprocess instead of the Python library. No Python runtime is bundled at
  all; Node.js drives everything.
- **Install size**: larger than the Python version (~150-200MB vs ~40MB) since
  Electron bundles a full Chromium + Node.js runtime. This is the direct
  tradeoff for the more polished UI.
- **Settings persistence**: `electron-store`, stored in the OS's standard
  app-data location instead of a JSON file in the home folder.

## What's included in this rewrite

- Auto-fetch on paste (no fetch button), with thumbnail preview
- Quality selection, Select2-style searchable dropdown
- Playlist and subtitle download toggles, with the same subtitle-429
  fallback behavior as the Python version (retries without subtitles if
  they can't be fetched, rather than failing the whole download)
- Batch queue: add multiple links, visible list with individual remove
- Resume support (`--continue`, yt-dlp's native resume)
- System tray: closing the window minimizes to tray, notifications when
  downloads finish
- Recent downloads list, Open Folder shortcut
- About dialog, update checker against GitHub Releases
- Settings (quality, folder, playlist, subtitles) remembered between sessions

## What still needs follow-up work

This was built and verified to launch, render, and handle its core
interactions correctly (dropdown, queue, modal, settings, error handling)
using a headless test in the build environment. What was **not** possible to
test:

- Actually running yt-dlp.exe and ffmpeg.exe as real Windows binaries and
  confirming a real download completes end to end
- The system tray icon and balloon notifications on a real Windows desktop
- The NSIS installer itself (untested build, same category of risk as the
  first few attempts at the Windows PyInstaller build and the Android
  build, both of which needed a couple of rounds of log-based fixes before
  they worked)

Expect the first CI build to need at least one round of fixes, the same way
the original Windows and Android builds did.

## Building locally

Requires Node.js 18+.

```
npm install
```

You'll also need `bin/yt-dlp.exe` and `bin/ffmpeg.exe` present before running
or building (these are intentionally not committed to the repository, and
are downloaded fresh by the GitHub Actions workflow on every build so the
download engine always stays current). To get them locally:

- yt-dlp.exe: https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
- ffmpeg.exe: extract from https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip

Then:

```
npm start          # run in development
npm run dist        # build the Windows installer (NSIS) into dist/
```

## Building via GitHub Actions (recommended, no local Windows machine needed)

This project lives in an `electron-app/` subfolder inside the existing
`NWGrabio` repository, alongside the original Python version, so the
website and the in-app update checker (both already pointing at that repo)
keep working without any changes. The workflow
(`.github/workflows/build-electron.yml`) only triggers on changes inside
`electron-app/`, so it won't interfere with the existing Python build.
It downloads yt-dlp.exe and ffmpeg.exe fresh, builds the installer, renames
it to `NWGrabio-Setup.exe` to match what the website expects, and uploads
it as a downloadable Actions artifact.

`GITHUB_REPO` in `src/main.js` is already set to `NethumWelikada/NWGrabio`
to match. If you ever move this to its own repository instead, update that
constant accordingly.

Developed by Nethum Welikada, Master of Engineering in Internetworking,
Dalhousie University, Halifax, Nova Scotia, Canada. MIT Licensed.
