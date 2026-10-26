@echo off
rem Double-click to install the VRChat + Unity server and skill into Bionic (LM Studio).
rem Needs Python 3.10+ on PATH. Safe to run again to update; config files are backed up as *.bak-mcp first.
cd /d "%~dp0"
python install.py vrchat-unity --target lmstudio
if errorlevel 1 (
  echo.
  echo Install failed. Check that Python 3.10+ is installed and on PATH, then try again.
) else (
  echo.
  echo Done. Restart Bionic / LM Studio to load the vrchat-unity tools.
)
pause
