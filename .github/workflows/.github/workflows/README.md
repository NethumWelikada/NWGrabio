# NWGrabio for Android

Same download engine as the Windows app (yt-dlp), rebuilt with a Kivy
touch interface for phones and tablets.

## What is different from the Windows version

- No ffmpeg is bundled, so there is no separate video+audio merge step.
  Quality options are limited to formats the source already offers as a
  single combined file: usually up to 1080p, sometimes higher depending
  on the site.
- "Open Folder" is replaced with "Open File", which uses Android's normal
  share/open dialog instead of a file manager window.
- Files save to `Download/NWGrabio` in the phone's shared storage.

## Getting the APK, no Android phone or dev machine needed

1. Push this whole repository to GitHub, including the `android/` folder.
2. Open the "Actions" tab, find "Build NWGrabio Android APK".
3. Wait for it to finish, 15 to 25 minutes on the first run, faster after
   that thanks to caching.
4. Download the `NWGrabio-APK` artifact from the finished run, unzip it.
5. Upload the `.apk` file inside to your website.

## Installing it on a phone

NWGrabio for Android is not on Google Play, since apps that download
video from platforms like YouTube routinely get removed for violating
those platforms' terms of service. This is normal for this category of
app; distributing the APK directly from a website is the standard path.

1. Download the `.apk` file from the website using the phone's browser.
2. Tap the downloaded file to install it.
3. Android will show a warning about installing from an unknown source.
   Tap Settings, allow installs from that source (usually the browser
   app), then go back and install.
4. Open NWGrabio, grant the storage permission when asked, paste a link,
   and download.

## Building locally instead of using GitHub Actions

Requires a Linux machine (or WSL on Windows) with Python 3.9+:

```
pip install buildozer cython
cd android
buildozer android debug
```

The finished APK appears in `android/bin/`.
