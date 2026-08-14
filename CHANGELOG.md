# Changelog

All notable changes to NWGrabio are documented here.

## 1.3.0

### Fixed
- Subtitle downloads no longer fail the whole download if the subtitle request gets rate limited (HTTP 429). NWGrabio now waits briefly before requesting subtitles, and automatically retries without subtitles if they still can't be fetched, so the video downloads either way.
- Removed a visual glitch where clicking buttons or checkboxes showed a dashed keyboard-focus outline around them.

## 1.2.0

### Added
- System tray support: closing the window now minimizes to the tray instead of quitting. Right click the tray icon to reopen or exit fully.
- Notifications when a download or batch finishes, even if the window is minimized to the tray.
- The download queue is now visible on screen, not just a count. Each queued link can be removed individually, or cleared all at once.
- Favicon added to the website.

### Changed
- Page and window titles now use a pipe separator ("NWGrabio | Grab Anything, From Anywhere.") instead of a hyphen.
- Window height increased slightly again to fit the queue list without any scrollbars.

## 1.1.0

### Added
- Batch downloads: click "+ Queue" to add multiple links before starting, they download one after another automatically.
- Subtitle download: check "Also save subtitles (.srt)" to save captions alongside the video.
- Resume support: if a download is cancelled or interrupted partway through, downloading the same link again continues from where it left off instead of restarting.
- The app now remembers your last-used quality setting between sessions.
- "Check for Updates" now available under the Help menu, in addition to the automatic check on launch.

### Changed
- Window height increased slightly to fit the new subtitle option without any scrollbars.

## 1.0.0

First public release.

- Download from YouTube, Facebook, TikTok, Instagram, Twitter/X, Vimeo, Reddit, and over 1000 other sites via the yt-dlp engine.
- Paste a link and details load automatically, no extra clicks.
- Quality selection up to 8K, 4K, 2K, Full HD, HD, SD, Low, or audio-only MP3.
- Playlist download support.
- Clean, brand colored interface with a Select2 style searchable quality dropdown.
- Recent downloads panel and Open Folder shortcut after a download finishes.
- Compact single page layout, no scrollbars, fits comfortably on any Windows display.
- Built-in "About & Help" reference and automatic update checking.
- MIT licensed, built on the open source yt-dlp and ffmpeg projects.
