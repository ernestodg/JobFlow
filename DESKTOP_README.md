# JobFlow Desktop Application

🚀 **Vibe Turbo Desktop Packaging Complete!**

A self-contained desktop application for job application tracking with native window support, local data storage, and offline functionality.

## Features

- **Native Desktop App**: Uses PyWebView for native window experience
- **Local Flask Server**: Boots on random free port automatically  
- **OS Data Directory**: Stores data in proper OS-specific locations
- **Demo Data Seeding**: First run includes sample job, follow-up, and journal
- **Offline Operation**: Fully functional without internet connection
- **Clean Shutdown**: Terminates server when window closes

## Quick Start

### Development Mode
```bash
# Run directly from source
python3 app_desktop.py
```

### Build Executable

**macOS:**
```bash
./scripts/build_mac.sh
```

**Windows:**
```cmd
scripts\build_win.bat
```

## Data Storage Locations

- **Windows**: `%LOCALAPPDATA%\JobFlow Tracker`
- **macOS**: `~/Library/Application Support/JobFlow Tracker`
- **Linux**: `~/.local/share/JobFlow Tracker`

## Architecture

### Files Structure
```
JobFlow/
├── app_desktop.py          # Desktop launcher
├── app/                    # Flask application package
│   ├── __init__.py        # App factory
│   ├── templates/         # HTML templates
│   ├── static/           # CSS/JS assets
│   └── api/
│       ├── __init__.py
│       └── routes.py     # API endpoints
├── seed_data/             # Demo data for first run
│   ├── jobs.json
│   ├── followups.json
│   └── journal.json
├── assets/                # App icons
├── scripts/               # Build scripts
└── requirements.txt       # Dependencies
```

### Dependencies

**Core:**
- `flask` - Web framework
- `waitress` - Production WSGI server
- `pywebview` - Native desktop window
- `platformdirs` - OS data directories

**Analytics:**
- `plotly` - Interactive charts
- `vaderSentiment` - Text sentiment analysis

**Packaging:**
- `PyInstaller` - Executable creation

## Build Process

1. **Development Setup**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Test Desktop App**:
   ```bash
   python3 app_desktop.py
   ```

3. **Create Executable**:
   - macOS: `./scripts/build_mac.sh`
   - Windows: `scripts\build_win.bat`

4. **Distribute**:
   - Single executable in `dist/` folder
   - No installation required
   - Self-contained with all dependencies

## Desktop App Behavior

### First Run
1. Creates OS data directory
2. Seeds demo data (1 job, 1 follow-up, 1 journal entry)
3. Opens native window at 1280×800
4. Serves dashboard at `http://127.0.0.1:<random-port>/`

### Subsequent Runs
1. Uses existing data directory
2. Preserves all user data
3. No re-seeding of demo data

### Shutdown
1. Window close confirmation
2. Clean server termination
3. All data automatically saved

## Technical Details

### Server Management
- **Port**: Automatically finds free port
- **Health Check**: Waits for server ready before opening window
- **Threading**: Server runs in daemon thread
- **Cleanup**: Hard exit ensures complete shutdown

### Data Management
- **Format**: JSON files for portability
- **Backup**: Automatic backup on save operations
- **Migration**: Handles schema version updates
- **Validation**: Input validation and error handling

### Window Management
- **Size**: 1280×800 default, resizable
- **Confirm Close**: Prevents accidental closure
- **Native**: Uses system WebView engine
- **Responsive**: Works with all dashboard features

## Deployment Checklist

✅ **Core Functionality**
- Flask app factory pattern
- Blueprint-based routes
- Native window integration
- OS data directory setup

✅ **Data Management**
- Demo data seeding
- JSON persistence
- Backup creation
- Schema validation

✅ **Build System**
- PyInstaller configuration
- Asset bundling
- Cross-platform scripts
- Dependency management

✅ **User Experience**
- Single-click launch
- No console window
- Confirm on close
- Proper error handling

## Usage Examples

### Launch App
```bash
# Double-click executable or:
./dist/JobFlowTracker  # macOS
dist\JobFlowTracker.exe  # Windows
```

### Development
```bash
# Run with live reload
python3 app_desktop.py

# Build for testing
./scripts/build_mac.sh && ./dist/JobFlowTracker
```

### Data Access
```python
# Data location programmatically
from platformdirs import user_data_dir
data_dir = user_data_dir("JobFlow Tracker", "pilotchoc")
print(f"Data stored at: {data_dir}")
```

## Build Results ✅

**macOS Build**: ✅ **SUCCESS**
- Executable: `dist/JobFlowTracker.app`
- Command Line: `dist/JobFlowTracker`
- Icon: Purple gradient with "JF" text and briefcase
- Size: Self-contained native app bundle
- Tested: ✅ Launches successfully

**Windows Build**: 📝 Ready (run `scripts\build_win.bat`)
- Target: `dist\JobFlowTracker.exe`
- Icon: Matching purple theme with "JF" branding

## Next Steps

1. **Code Signing**: Sign executables for distribution
2. **Installer**: Optional installer wrapper  
3. **Auto-Updates**: Version checking and update mechanism
4. **Logging**: User-accessible log files in data directory
5. **Distribution**: App store or direct download

---

🎉 **Desktop packaging complete and tested!** The macOS app builds successfully and runs as a native desktop application.