# NWGrabio

Grab Anything, From Anywhere. A free, open source Windows app for
downloading video and audio from YouTube, TikTok, Instagram, Facebook,
and 1,000+ other sites, built with Electron.

## Requirements

- Node.js 18 or newer
- Windows, to actually run and build the installer (the app targets
  Windows only)

## Setup

1. Clone or download this repository.
2. Install dependencies:

```
npm install
```

3. Download the two engine binaries into the `bin/` folder (not committed
   to the repo, so the download engine always stays current):

- `bin/yt-dlp.exe` from
  https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
- `bin/ffmpeg.exe`, extracted from
  https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
  (the `ffmpeg.exe` file is inside the `bin` folder of that zip)

## Run in development

```
npm start
```

## Build the Windows installer

```
npm run dist
```

The finished installer appears in `dist/`.

## Project structure

```
src/main.js         Electron main process: window, tray, yt-dlp control
src/preload.js       IPC bridge exposed to the renderer
renderer/            The UI (HTML/CSS/JS)
assets/               App icons
bin/                  yt-dlp.exe and ffmpeg.exe go here (not committed)
```

Developed by Nethum Welikada, Master of Engineering in Internetworking,
Dalhousie University, Halifax, Nova Scotia, Canada. MIT Licensed.
