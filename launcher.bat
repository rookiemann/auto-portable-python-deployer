@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON_DIR=%SCRIPT_DIR%python_embedded"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

:: Handle commands
if /i "%~1"=="setup" (
    echo Running full setup...
    call "%SCRIPT_DIR%install.bat"
    goto :eof
)

if /i "%~1"=="help" (
    echo.
    echo   Auto Portable Python Deployer - Launcher
    echo   =========================================
    echo.
    echo   Usage:
    echo     launcher.bat               Launch the Deployer GUI
    echo     launcher.bat cli [args]    Generate packages from command line
    echo     launcher.bat setup         Run full install/setup
    echo     launcher.bat help          Show this help
    echo.
    echo   CLI Examples:
    echo     launcher.bat cli --name MyApp --python 3.12
    echo     launcher.bat cli --name WebServer --python 3.13 -r requirements.txt --git
    echo     launcher.bat cli --name MLProject --python 3.10 -ri "torch,numpy" --no-tkinter
    echo     launcher.bat cli --list-versions
    echo     launcher.bat cli --help
    echo.
    goto :eof
)

:: Check if Python is installed
if not exist "%PYTHON_EXE%" (
    echo Python not found. Running first-time setup...
    echo.
    call "%SCRIPT_DIR%install.bat" %*
    goto :eof
)

:: Launch (GUI or CLI depending on arguments)
cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" "%SCRIPT_DIR%deployer_app.py" %*

endlocal
