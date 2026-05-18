@echo off
:: ============================================================
::  Visio Eye — Windows installer build orchestrator.
::
::  Requirements (installed once on the build machine):
::    * Python 3.11+  (https://python.org)         python --version
::    * PyInstaller    pip install pyinstaller
::    * Inno Setup 6   https://jrsoftware.org/isdl.php
::      and `iscc.exe` on PATH (Inno bin directory)
::
::  Optional: drop ffmpeg.exe + ffprobe.exe into
::      installer\windows\ffmpeg\
::  to bundle FFmpeg into the installer (recommended; otherwise users
::  must install FFmpeg themselves).
::
::  Run from the project root:
::      installer\windows\build_windows.bat
::
::  Output: dist\VisioEye-1.4.0-setup.exe
:: ============================================================
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."
set "PROJECT_DIR=%CD%"
set "VISIO_EYE_PROJECT_DIR=%PROJECT_DIR%"

echo.
echo === [1/5] Sanity check ===========================================
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: python is not on PATH. Install Python 3.11+ and reboot.
    exit /b 1
)
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install --upgrade pip pyinstaller || exit /b 1
)

echo.
echo === [2/5] Install runtime requirements ===========================
python -m pip install --upgrade -r requirements.txt || exit /b 1

echo.
echo === [3/5] Refresh logo.ico ======================================
python -c "from PIL import Image; im=Image.open('assets/img/logo.png').convert('RGBA'); im.save('assets/img/logo.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"

:: Auto-download FFmpeg + Visual C++ Redistributable — the end-user
:: installer must work OFFLINE on a fresh Windows machine, so every
:: external dependency is fetched once here at build time and embedded
:: in the .exe.

if not exist "installer\windows\ffmpeg" mkdir "installer\windows\ffmpeg"

if not exist "installer\windows\ffmpeg\ffmpeg.exe" (
    echo Downloading FFmpeg static build from gyan.dev...
    powershell -NoProfile -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile installer\windows\ffmpeg.zip; Expand-Archive installer\windows\ffmpeg.zip -DestinationPath installer\windows\ffmpeg_tmp -Force; Get-ChildItem installer\windows\ffmpeg_tmp -Recurse -Filter ffmpeg.exe | Select-Object -First 1 | Copy-Item -Destination installer\windows\ffmpeg\; Get-ChildItem installer\windows\ffmpeg_tmp -Recurse -Filter ffprobe.exe | Select-Object -First 1 | Copy-Item -Destination installer\windows\ffmpeg\; Remove-Item installer\windows\ffmpeg.zip; Remove-Item installer\windows\ffmpeg_tmp -Recurse -Force" || (
        echo WARNING: FFmpeg auto-download failed.  See README for manual steps.
    )
)

if not exist "installer\windows\vc_redist.x64.exe" (
    echo Downloading Microsoft Visual C++ 2015-2022 Redistributable...
    powershell -NoProfile -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile installer\windows\vc_redist.x64.exe" || (
        echo WARNING: VC++ Redistributable auto-download failed.  End users
        echo on stripped Windows installs may need to install it themselves.
    )
)

echo.
echo === [4/5] Run PyInstaller =======================================
if exist build rmdir /s /q build
if exist dist\visio-eye rmdir /s /q dist\visio-eye
python -m PyInstaller installer\windows\visio-eye.spec --noconfirm || exit /b 1

echo.
echo === [5/5] Compile installer with Inno Setup =====================
where iscc >nul 2>nul
if errorlevel 1 (
    echo WARNING: iscc.exe not on PATH. Skipping installer compilation.
    echo Install Inno Setup 6 from https://jrsoftware.org/isdl.php then
    echo re-run this script, or open visio-eye.iss in the Inno IDE.
    echo PyInstaller output is in: dist\visio-eye\
    exit /b 0
)
iscc installer\windows\visio-eye.iss || exit /b 1

echo.
echo ============================================================
echo  Build complete.
echo  Installer:  dist\VisioEye-1.4.0-setup.exe
echo  Portable :  dist\visio-eye\visio-eye.exe
echo ============================================================
echo.
echo  TIP: this installer matches your current Python bitness.
echo       For BOTH 64-bit and 32-bit support, run this script
echo       twice -- once with 64-bit Python, once with 32-bit
echo       Python -- and rename the outputs accordingly.
endlocal
