@echo off
title Face to Web to Blockchain
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

set PY_EXE=%~dp0.venv\Scripts\python.exe
set PIP_EXE=%~dp0.venv\Scripts\pip.exe

where python >nul 2>nul
if errorlevel 1 goto no_python

if not exist "%PY_EXE%" goto setup_venv

"%PY_EXE%" -c "import flask, rich, cv2, numpy, PIL, onnxruntime, insightface" >nul 2>nul
if errorlevel 1 goto install_packages

goto menu

:setup_venv
echo [*] Creating virtual environment (.venv)...
python -m venv .venv
if errorlevel 1 goto venv_error
echo [*] Virtual environment created.
goto install_packages

:install_packages
echo [*] Setting up dependencies in .venv...
"%PY_EXE%" -m pip install --upgrade pip
"%PIP_EXE%" install "numpy<2.0" opencv-python "Pillow>=10.0" "requests>=2.31" "python-dotenv>=1.0" "rich>=13.0" "flask>=3.0" "web3>=7.0" "py-solc-x>=2.0" "pytest>=8.0" "pytest-cov>=5.0" onnxruntime onnx tqdm prettytable scipy scikit-learn scikit-image matplotlib cython easydict "albumentations==1.3.1" PyYAML
"%PIP_EXE%" install --no-deps "https://github.com/Gourieff/Assets/raw/main/Insightface/insightface-0.7.3-cp311-cp311-win_amd64.whl"
"%PIP_EXE%" install "numpy<2.0"
if not exist ".env" (
    if exist ".env.example" copy .env.example .env >nul
)
goto menu

:menu
cls
echo ============================================================
echo      Face -^> Web -^> Blockchain Launcher
echo ============================================================
echo.
echo   1. Start Web Interface (http://localhost:5000)
echo   2. Run CLI Pipeline
echo   3. Exit
echo.
echo ============================================================
set /p choice=Enter choice (1-3): 

if "%choice%"=="1" goto run_web
if "%choice%"=="2" goto run_custom
if "%choice%"=="3" goto exit_app

echo.
echo Invalid selection.
ping -n 2 127.0.0.1 >nul
goto menu

:run_web
cls
echo Starting Web Server...
echo Opening http://localhost:5000 in your browser...
start "" http://localhost:5000
"%PY_EXE%" run_web.py
echo.
pause
goto menu

:run_custom
cls
echo ============================================================
echo Run CLI Pipeline
echo ============================================================
echo Usage: python -m app.main --image ^<path^> [--mock-search] [--skip-blockchain] [--tamper-demo]
echo.
set /p img_path=Enter image path (default: sample/virat-kohli-photo-4k.webp): 
if "%img_path%"=="" set img_path=sample/virat-kohli-photo-4k.webp

echo.
echo Search Mode:
echo   1. Mock Search (Offline / no API key)
echo   2. Live Search (Google Lens via SerpApi)
set /p smode=Choose (1 or 2): 

set SFLAGS=
if "%smode%"=="1" set SFLAGS=--mock-search

echo.
echo Blockchain Mode:
echo   1. Local Verification (Skip Blockchain)
echo   2. On-Chain Polygon Amoy
set /p bmode=Choose (1 or 2): 

set BFLAGS=
if "%bmode%"=="1" set BFLAGS=--skip-blockchain

echo.
echo Running: "%PY_EXE%" -m app.main --image "%img_path%" %SFLAGS% %BFLAGS% --tamper-demo
echo.
"%PY_EXE%" -m app.main --image "%img_path%" %SFLAGS% %BFLAGS% --tamper-demo
echo.
pause
goto menu

:no_python
echo [ERROR] Python is not found on your system PATH.
echo Please install Python 3.10 or 3.11 from https://www.python.org/
pause
exit /b 1

:venv_error
echo [ERROR] Failed to create virtual environment.
pause
exit /b 1

:exit_app
exit /b 0
