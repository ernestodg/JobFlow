@echo off
setlocal

REM Always run from this script's directory so relative paths in app.py work.
pushd "%~dp0"

set "SERVER_URL=http://127.0.0.1:5001"

REM Open the dashboard in a browser tab/window.
start "JobFlow" "%SERVER_URL%"

REM Prefer project virtual environment, then py launcher, then python.
if exist "%~dp0.venv\Scripts\python.exe" (
	"%~dp0.venv\Scripts\python.exe" app.py
) else (
	where py >nul 2>&1
	if %errorlevel%==0 (
		py app.py
	) else (
		python app.py
	)
)

set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%