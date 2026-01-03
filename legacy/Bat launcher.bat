@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURATION ---
set "VENV_PATH=.venv"
set "REQ_FILE=requirements.txt"
set "APP_FILE=SpotDLPro_v3.py"
set "FFMPEG_DIR=ffmpeg"

title SpotDL-Pro: Pre-flight Check

echo ====================================================
echo          SpotDL-Pro v3 - System Launcher
echo ====================================================

:: 1. Check for Python Installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b
)

:: 2. Python Version Check (Fixed Logic)
for /f "tokens=2 delims= " %%a in ('python --version') do set "PY_VER=%%a"
echo [SYSTEM] Detected Python %PY_VER%

:: Checking specifically for 3.13 without the crashing IF block
echo %PY_VER% | find "3.13" >nul
if %errorlevel% equ 0 (
    echo [!] WARNING: Python 3.13 detected.
    echo [!] Note: yt-dlp/pydantic might be unstable on 3.13.
)

:: 3. Virtual Environment Check/Activation
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv %VENV_PATH%
)

echo [INFO] Activating environment...
call "%VENV_PATH%\Scripts\activate.bat"

:: 4. Dependency Integrity Check
echo [INFO] Synchronizing dependencies...
:: Using -m pip is safer for 3.13 pathing
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r "%REQ_FILE%"

:: 5. FFmpeg Binary Validation
echo [INFO] Checking for FFmpeg...
if exist "%FFMPEG_DIR%\ffmpeg.exe" (
    echo [SUCCESS] Local FFmpeg detected in /%FFMPEG_DIR%
) else (
    ffmpeg -version >nul 2>&1
    if !errorlevel! equ 0 (
        echo [SUCCESS] FFmpeg detected in system PATH.
    ) else (
        echo [WARNING] FFmpeg NOT FOUND. 
        echo [!] Downloads will fail. Place ffmpeg.exe in /%FFMPEG_DIR%
    )
)

:: 6. Final Engine Sanity Test
echo [INFO] Finalizing Engine...
python -c "import spotdl; import psutil; print('Ready')" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Engine failed to initialize. 
    echo [!] Try running: python -m pip install spotdl psutil
    pause
    exit /b
)

:: 7. Launch Application
echo [SUCCESS] All systems go. Launching UI...
echo ----------------------------------------------------
:: Use "" for the title argument of start
start "" python "%APP_FILE%"
exit /b