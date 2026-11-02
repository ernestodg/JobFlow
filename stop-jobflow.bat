@echo off
setlocal enabledelayedexpansion

set "PORT=5001"
set "FOUND=0"
set "KILLED=0"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
	set "FOUND=1"
	echo Stopping JobFlow server on port %PORT% - PID %%P...
	taskkill /PID %%P /F
	if !errorlevel! equ 0 (
		set "KILLED=1"
		echo PID %%P stopped.
	) else (
		echo Failed to stop PID %%P.
	)
)

if "!FOUND!"=="0" (
	echo No listening process found on port %PORT%.
) else if "!KILLED!"=="1" (
	echo Server stop command completed.
) else (
	echo Found process entries on port %PORT%, but termination failed.
)

endlocal