@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo   Auto Portable Python Deployer - Setup
echo ============================================
echo.
echo   This script sets up everything from scratch:
echo   - Embedded Python 3.12 (no system Python needed)
echo   - Tkinter GUI framework
echo   - All Python dependencies
echo   - Then launches the Deployer GUI
echo.

set "SCRIPT_DIR=%~dp0"
set "PYTHON_DIR=%SCRIPT_DIR%python_embedded"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

set "PYTHON_VERSION=3.12.10"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_ZIP=%SCRIPT_DIR%python_embedded.zip"

:: ============================================
:: Step 1: Download Embedded Python
:: ============================================
if exist "%PYTHON_EXE%" (
    echo [OK] Embedded Python already installed.
    goto :check_pip
)

echo [1/6] Downloading Python %PYTHON_VERSION% embedded...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'"

if not exist "%PYTHON_ZIP%" (
    echo.
    echo ERROR: Failed to download Python.
    echo   - Check your internet connection
    echo   - URL: %PYTHON_URL%
    echo.
    pause
    exit /b 1
)

echo [2/6] Extracting Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python extraction failed.
    pause
    exit /b 1
)

del "%PYTHON_ZIP%" 2>nul

:: ============================================
:: Step 2: Configure ._pth for site-packages
:: ============================================
echo [3/6] Configuring Python for package installation...

:: Create Lib\site-packages directory
if not exist "%PYTHON_DIR%\Lib\site-packages" (
    mkdir "%PYTHON_DIR%\Lib\site-packages"
)

:: Rewrite the ._pth file to enable import site and site-packages
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pthFiles = Get-ChildItem '%PYTHON_DIR%\python*._pth'; if ($pthFiles.Count -gt 0) { $pth = $pthFiles[0]; $zipName = (Get-ChildItem '%PYTHON_DIR%\python*.zip' | Select-Object -First 1).Name; if (-not $zipName) { $zipName = 'python312.zip' }; $content = @($zipName, '.', 'Lib', 'Lib\site-packages', 'DLLs', '', 'import site'); $content | Set-Content -Path $pth.FullName -Encoding ASCII; Write-Host '   Configured:' $pth.Name } else { Write-Host 'WARNING: No ._pth file found' }"

:: ============================================
:: Step 3: Bootstrap pip (via get-pip.py)
:: ============================================
:check_pip
"%PYTHON_EXE%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [3/6] Downloading get-pip.py...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"

    if not exist "%PYTHON_DIR%\get-pip.py" (
        echo ERROR: Failed to download get-pip.py.
        pause
        exit /b 1
    )

    echo [3/6] Installing pip...
    "%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py"
    if errorlevel 1 (
        echo ERROR: Failed to install pip.
        pause
        exit /b 1
    )

    del "%PYTHON_DIR%\get-pip.py" 2>nul
    "%PYTHON_EXE%" -m pip install --upgrade pip 2>nul
) else (
    echo [OK] pip already available.
)

:: ============================================
:: Step 4: Set up tkinter (needed for GUI)
:: ============================================
"%PYTHON_EXE%" -c "import _tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [4/6] Setting up tkinter for GUI...

    set "TCLTK_MSI_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/amd64/tcltk.msi"
    set "TCLTK_MSI=%SCRIPT_DIR%_tcltk.msi"
    set "TCLTK_DIR=%SCRIPT_DIR%_tcltk_extract"

    echo   Downloading tcltk.msi...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '!TCLTK_MSI_URL!' -OutFile '!TCLTK_MSI!'"

    if not exist "!TCLTK_MSI!" (
        echo WARNING: Failed to download tcltk.msi. GUI may not work.
        goto :tkinter_done
    )

    echo   Extracting tkinter components...
    if exist "!TCLTK_DIR!" rmdir /S /Q "!TCLTK_DIR!" 2>nul
    powershell -NoProfile -Command "Start-Process -FilePath 'msiexec.exe' -ArgumentList '/a','!TCLTK_MSI!','/qn','TARGETDIR=!TCLTK_DIR!' -Wait -NoNewWindow"

    :: Copy DLLs next to python.exe
    if exist "!TCLTK_DIR!\DLLs\_tkinter.pyd" (
        copy /Y "!TCLTK_DIR!\DLLs\_tkinter.pyd" "%PYTHON_DIR%\" >nul 2>&1
        copy /Y "!TCLTK_DIR!\DLLs\tcl86t.dll" "%PYTHON_DIR%\" >nul 2>&1
        copy /Y "!TCLTK_DIR!\DLLs\tk86t.dll" "%PYTHON_DIR%\" >nul 2>&1
        if exist "!TCLTK_DIR!\DLLs\zlib1.dll" (
            copy /Y "!TCLTK_DIR!\DLLs\zlib1.dll" "%PYTHON_DIR%\" >nul 2>&1
        )
    )

    :: Copy Lib/tkinter/ Python package
    if exist "!TCLTK_DIR!\Lib\tkinter" (
        if exist "%PYTHON_DIR%\Lib\tkinter" rmdir /S /Q "%PYTHON_DIR%\Lib\tkinter" 2>nul
        xcopy /E /I /Y "!TCLTK_DIR!\Lib\tkinter" "%PYTHON_DIR%\Lib\tkinter" >nul 2>&1
    )

    :: Copy tcl/ library (tcl8.6, tk8.6)
    if exist "!TCLTK_DIR!\tcl" (
        if exist "%PYTHON_DIR%\tcl" rmdir /S /Q "%PYTHON_DIR%\tcl" 2>nul
        xcopy /E /I /Y "!TCLTK_DIR!\tcl" "%PYTHON_DIR%\tcl" >nul 2>&1
    )

    :: Cleanup
    rmdir /S /Q "!TCLTK_DIR!" 2>nul
    del "!TCLTK_MSI!" 2>nul

    :: Verify
    "%PYTHON_EXE%" -c "import _tkinter" >nul 2>&1
    if errorlevel 1 (
        echo WARNING: Failed to set up tkinter. GUI may not work.
    ) else (
        echo [OK] tkinter setup complete.
    )
) else (
    echo [OK] tkinter already available.
)
:tkinter_done

:: ============================================
:: Step 5: Install deployer requirements
:: ============================================
echo [5/6] Installing deployer requirements...
"%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet 2>nul
if errorlevel 1 (
    echo Retrying with verbose output...
    "%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install requirements.
        pause
        exit /b 1
    )
)

:: ============================================
:: Step 6: Launch the deployer GUI
:: ============================================
echo [6/6] Launching Portable Python Deployer...
echo.
echo ============================================
echo.

cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" "%SCRIPT_DIR%deployer_app.py" %*

if errorlevel 1 (
    echo.
    echo The deployer exited with an error.
    echo.
    pause
)

endlocal
