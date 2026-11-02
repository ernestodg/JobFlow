#!/usr/bin/env bash
# macOS build script for JobFlow Tracker desktop app

set -e

NAME="JobFlowTracker"

echo "Building $NAME for macOS..."

pyinstaller app_desktop.py \
  --name "$NAME" \
  --onefile \
  --windowed \
  --icon assets/icon.icns \
  --add-data "app/templates:app/templates" \
  --add-data "app/static:app/static" \
  --add-data "seed_data:seed_data"

echo "Build complete: dist/$NAME"

if [ -f "dist/$NAME" ]; then
    echo "Success: Executable created at dist/$NAME"
    echo "You can run it with: ./dist/$NAME"
else
    echo "Error: Build failed!"
    exit 1
fi