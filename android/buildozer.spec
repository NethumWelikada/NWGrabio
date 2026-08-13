[app]
title = NWGrabio
package.name = nwgrabio
package.domain = io.github.nethumwelikada

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0

requirements = python3==3.11.9,hostpython3==3.11.9,kivy,yt-dlp,certifi,pyjnius

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
