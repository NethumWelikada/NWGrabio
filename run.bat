@echo off
REM Developer option: runs NWGrabio straight from source, without building
REM an exe or installer. Useful while making changes to main.py.
REM For a normal installable program, use build.bat instead, which produces
REM NWGrabio-Setup.exe.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python was not found in PATH. Install Python 3.9 or newer from python.org
    pause
    exit /b 1
)

if not exist build_env (
    echo First time setup. Creating environment and installing dependencies...
    python -m venv build_env
    call build_env\Scripts\activate.bat
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call build_env\Scripts\activate.bat
)

python main.py
pause
