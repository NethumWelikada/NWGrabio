@echo off
REM NWGrabio build script for Windows
REM Developed by Nethum Welikada, Dalhousie University
REM
REM This script does two things:
REM   1. Compiles NWGrabio.exe with PyInstaller (yt-dlp and ffmpeg bundled
REM      inside, nothing extra to install for whoever runs the exe).
REM   2. If Inno Setup is installed, compiles a real Windows installer
REM      called NWGrabio-Setup.exe with a Next / Next / Install wizard,
REM      Start Menu and Desktop shortcuts, and an uninstaller.

echo ============================================
echo   NWGrabio - Build Script
echo ============================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python was not found in PATH. Install Python 3.9 or newer from python.org
    echo and make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv build_env
call build_env\Scripts\activate.bat

echo Installing dependencies, including the bundled ffmpeg engine...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Building NWGrabio with yt-dlp and ffmpeg bundled inside...
echo Using onedir mode: this avoids the self-extracting behavior of onefile
echo builds, which many antivirus engines flag as suspicious even when the
echo app is completely clean.
pyinstaller --noconfirm --onedir --windowed ^
  --name NWGrabio ^
  --icon icon.ico ^
  --version-file file_version_info.txt ^
  --collect-all imageio_ffmpeg ^
  main.py

if not exist dist\NWGrabio\NWGrabio.exe (
    echo.
    echo Build failed. See the messages above for details.
    pause
    exit /b 1
)

echo.
echo dist\NWGrabio\NWGrabio.exe created successfully.
echo.

REM Look for the Inno Setup compiler in its usual install locations.
set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe

if defined ISCC (
    echo Inno Setup found. Building NWGrabio-Setup.exe installer...
    "%ISCC%" installer.iss
    echo.
    echo ============================================
    echo Build finished.
    echo Standalone app folder: dist\NWGrabio\
    echo Setup installer:       Output\NWGrabio-Setup.exe
    echo.
    echo Give NWGrabio-Setup.exe to anyone. They just double click it and
    echo follow the wizard, like installing any normal Windows program.
    echo ============================================
) else (
    echo Inno Setup was not found, so only the standalone app was built.
    echo.
    echo To also get a proper Setup.exe installer with a wizard, Start Menu
    echo shortcut, and uninstaller:
    echo   1. Download Inno Setup, free, from https://jrsoftware.org/isdl.php
    echo   2. Install it with default options.
    echo   3. Run build.bat again.
    echo.
    echo ============================================
    echo Build finished.
    echo Standalone app folder: dist\NWGrabio\
    echo ============================================
)

pause
