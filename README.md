# NWGrabio

Universal Video Downloader for Windows. Download from YouTube, Facebook, TikTok, Instagram, Twitter/X, Vimeo, Reddit and hundreds of other sites, up to the highest resolution available including 4K and 8K, with a clean, brand colored interface.

Developed by Nethum Welikada
Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada
GitHub: github.com/NethumWelikada

---

## What you end up with

Running the build once produces a normal Windows installer, **NWGrabio-Setup.exe**. Anyone can double click it and click through Next, Next, Install, Finish, exactly like installing any commercial program. It adds:

- A Start Menu entry
- An optional Desktop shortcut
- An entry in "Add or Remove Programs" with a working uninstaller

The engine that does the downloading, yt-dlp, and the tool needed to combine high resolution video and audio streams, ffmpeg, are both bundled inside the app itself. Nobody who installs NWGrabio needs to install Python, yt-dlp, or ffmpeg separately. Those tools are only needed once, by you, to build the installer.

---

## What is inside this package

```
NWGrabio/
  main.py               The application source code
  requirements.txt      Python dependencies used only for building
  file_version_info.txt  Publisher and product metadata embedded into the exe
  build.bat              Builds NWGrabio AND NWGrabio-Setup.exe
  installer.iss           Inno Setup script that defines the installer wizard
  run.bat                 Optional: run the app from source while developing
  icon.ico                 Application icon
  README.md                This guide
```

---

## The fastest way to get NWGrabio-Setup.exe: let GitHub build it for you

You do not need a Windows computer for this. GitHub can compile the real Windows installer for you automatically, for free, using its own Windows machines.

1. Create a free account at https://github.com if you do not already have one.
2. Create a new repository, for example named `NWGrabio`.
3. Upload every file and folder from this package into that repository, including the hidden `.github` folder. On github.com you can drag and drop files directly onto the "Add file > Upload files" page, or use git if you have it installed.
4. Click the "Actions" tab at the top of the repository.
5. A workflow called "Build NWGrabio Windows Installer" will start automatically. Wait three to five minutes for it to finish, shown by a green checkmark.
6. Click into that finished run, scroll down to "Artifacts", and download the one named `NWGrabio-Setup`.
7. Unzip what you downloaded. Inside is `NWGrabio-Setup.exe`, the real, ready to distribute installer.
8. Upload `NWGrabio-Setup.exe` to your website. Anyone who downloads and runs it gets the normal Windows install wizard, Next, Next, Install, Finish, with a Start Menu entry, desktop shortcut option, and uninstaller. They never see any code, scripts, or Python.

This also means that any time you change `main.py` in the future and push the update to GitHub, a fresh `NWGrabio-Setup.exe` is built automatically without you doing anything else.

---

## Alternative: build it yourself on a Windows PC

If you do have access to a Windows computer, you can build the same file locally instead of using GitHub.

## About the "Windows protected your PC" warning

When someone runs `NWGrabio-Setup.exe` for the first time, Windows SmartScreen may show a blue "Windows protected your PC" screen. This is standard behavior for any new application from any developer, not a sign of a problem with NWGrabio. It happens because SmartScreen trusts files based on two things: whether they carry a paid code-signing certificate, and how many people have already run that exact file (its "reputation"). A brand new file has neither yet.

What this build already does to minimize false flags:
- Uses PyInstaller's onedir mode instead of onefile. Onefile builds self-extract to a temporary folder every time they run, which many antivirus engines flag as suspicious behavior even when the app is harmless. Onedir avoids that pattern entirely, at the cost of shipping a small folder of files instead of a single exe, which the Setup installer already handles for you.
- Embeds real publisher and product metadata into the executable (via `file_version_info.txt`), so right-clicking NWGrabio.exe and choosing Properties > Details shows a real company name, product name, and version instead of blank fields.

What removes the warning completely:
- A code-signing certificate. These are issued by certificate authorities such as DigiCert, Sectigo, or SSL.com, typically 100 to 400 USD per year for a standard certificate, or immediate SmartScreen trust with an Extended Validation certificate at a higher cost. Once signed, you use `signtool.exe` (comes with the Windows SDK) to sign `dist\NWGrabio\NWGrabio.exe` before building the installer.
- For open source projects specifically, SignPath.io offers free code signing, including a GitHub Actions integration, through their open source program. Worth looking into if you plan to distribute NWGrabio publicly and want a fully clean install experience without paying.
- Regardless of signing, reputation still builds over time and downloads. You can speed this up slightly by submitting your build to Microsoft directly at https://www.microsoft.com/en-us/wdsi/filesubmission for analysis.

Telling users "click More info, then Run anyway" on your download page is normal, common practice for independent developers distributing unsigned software, and does not indicate anything is wrong with the file.




1. Go to https://www.python.org/downloads/
2. Download the latest Python 3 installer for Windows.
3. Run it. On the first screen, check "Add python.exe to PATH" before clicking Install Now.
4. Confirm it worked by opening Command Prompt and typing:
```
python --version
```

## Step 2: Install Inno Setup (one time, only needed to build the installer)

Inno Setup is the free tool that turns the app into a real Setup.exe wizard.

1. Go to https://jrsoftware.org/isdl.php
2. Download and run the installer, keep the default options.

If you skip this step, `build.bat` will still work and will produce `dist\NWGrabio\NWGrabio.exe`, a standalone app you can run directly. It just will not produce the Setup wizard version. You can install Inno Setup later and rerun `build.bat` at any time.

---

## Step 3: Extract this package

Extract NWGrabio.zip to a folder of your choice, for example `C:\NWGrabio`.

---

## Step 4: Build

Double click `build.bat` and wait. It will:

1. Create a private Python environment inside the folder so nothing is installed system-wide.
2. Install yt-dlp, ffmpeg's engine, and PyInstaller into that environment.
3. Compile everything into `dist\NWGrabio\NWGrabio.exe`, along with a folder of supporting files, with yt-dlp and ffmpeg built in.
4. If Inno Setup is installed, automatically compile `Output\NWGrabio-Setup.exe`, the installer wizard.

This takes one to three minutes depending on your machine and only needs to be done once, or again later if you change `main.py`.

---

## Step 5: Install and run

1. Open the `Output` folder and run `NWGrabio-Setup.exe`.
2. Follow the wizard: choose whether to create a desktop shortcut, choose the install folder if you want something other than the default, click Install.
3. Click Finish. NWGrabio is now installed like any other Windows program and can be launched from the Start Menu or its desktop shortcut.
4. To remove it later, use "Add or Remove Programs" in Windows Settings, same as any other app.

You can also skip the installer and just hand someone the whole `dist\NWGrabio\` folder directly and have them run `NWGrabio.exe` inside it, it runs standalone with no installation step, though it will not appear in the Start Menu or Add/Remove Programs.

---

## How to use NWGrabio

1. Copy a video link from YouTube, Facebook, TikTok, Instagram, or any other supported site.
2. Paste it into the URL box, or click "Paste". NWGrabio fetches the title, thumbnail, and duration automatically, no extra click needed.
3. Choose a quality from the dropdown:
   - Best Available (Auto, up to 8K): picks the single highest quality stream that exists for that video
   - 8K, 4K, 2K, Full HD, HD, SD, Low: caps the download at that resolution or below
   - Audio Only (MP3): extracts just the audio track
4. If the link is part of a playlist and you want every video, check "Download the full playlist".
5. Choose the folder to save into, or leave it on the default Downloads folder.
6. Click "Download". Progress, speed, and estimated time remaining are shown live, along with an activity log and a recent downloads list.
7. Click "Cancel" at any time to stop an in-progress download.
8. When it finishes, click "Open Folder" to jump straight to the downloaded file in Windows Explorer.

A full walkthrough is also always available inside the app itself, under the "About & Help" tab.

---

## Supported sites

NWGrabio uses the yt-dlp engine, which supports well over one thousand websites, including:

- YouTube (videos, shorts, playlists as single videos)
- Facebook (public videos and reels)
- TikTok
- Instagram (public posts and reels)
- Twitter / X
- Vimeo
- Reddit
- Dailymotion
- Twitch clips
- And many general news, blog, and media sites

Some sites may require the content to be public, or may restrict downloads based on their own settings; this is outside the app's control.

---

## Updating the download engine

Sites occasionally change how their pages work, which can require an updated yt-dlp. To refresh it and rebuild:

1. Open Command Prompt inside the NWGrabio folder.
2. Run:
```
build_env\Scripts\activate.bat
pip install --upgrade yt-dlp
```
3. Run `build.bat` again to rebuild `NWGrabio.exe` and `NWGrabio-Setup.exe` with the update.

---

## Developer option: run without building

If you are editing `main.py` and want to test quickly without building an exe each time, double click `run.bat` instead. It installs the same dependencies into a local environment and launches the app directly from source.

---

## Troubleshooting

**"yt-dlp is not installed" or "ffmpeg was not detected" inside the app**
This means you launched `main.py` directly with a plain Python install that never had `pip install -r requirements.txt` run against it. Use `run.bat` for development, or better, use `build.bat` to produce the self-contained `NWGrabio.exe` and `NWGrabio-Setup.exe`, which have both bundled in and never show this message.

**Inno Setup section is skipped during build.bat**
This means Inno Setup is not installed. Install it from https://jrsoftware.org/isdl.php with default settings, then run `build.bat` again. `dist\NWGrabio\NWGrabio.exe` still works fine on its own in the meantime.

**Windows SmartScreen warning when opening NWGrabio-Setup.exe or NWGrabio.exe**
This is expected for any new, unsigned application. Click "More info" then "Run anyway". This happens because the app is not yet code-signed with a paid certificate, not because of a virus.

**A specific site fails to download**
Update yt-dlp using the steps above, since site support is updated frequently, then rebuild.

---

## License and credit

NWGrabio is released under the MIT License, see the `LICENSE` file included in this package and in the installed program folder. This means anyone is free to use, modify, and share it, provided the original copyright notice is kept.

It combines a custom brand colored interface with the open source yt-dlp project (https://github.com/yt-dlp/yt-dlp) and ffmpeg, both used under their own open source licenses, credited in full inside `LICENSE`.

Developed by Nethum Welikada
Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada
GitHub: github.com/NethumWelikada
