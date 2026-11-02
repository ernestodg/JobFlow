@echo off
REM Windows build script for JobFlow Tracker desktop app

set NAME=JobFlowTracker

echo Building %NAME% for Windows...

pyinstaller app_desktop.py ^
  --name %NAME% ^
  --onefile ^
  --noconsole ^
  --icon assets\icon.ico ^
  --add-data "app\templates;app\templates" ^
  --add-data "app\static;app\static" ^
  --add-data "seed_data;seed_data"

echo Build complete: dist\%NAME%.exe

if exist dist\%NAME%.exe (
    echo Success: Executable created at dist\%NAME%.exe
) else (
    echo Error: Build failed!
    exit /b 1
)