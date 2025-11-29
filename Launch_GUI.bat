@echo off
REM Thorlabs Motion Control GUI Launcher
REM Double-click this file to launch the GUI

cd /d "%~dp0"

REM Use full path to Anaconda Python where pythonnet is installed
set PYTHON_EXE=C:\Users\jovanm\anaconda3\python.exe

REM Check if the Python executable exists
if not exist "%PYTHON_EXE%" (
    echo Python not found at: %PYTHON_EXE%
    echo Please update PYTHON_EXE in this batch file to point to your Python installation.
    pause
    exit /b 1
)

"%PYTHON_EXE%" launch_gui.py

if errorlevel 1 (
    echo.
    echo Failed to launch GUI. Make sure dependencies are installed.
    echo Required: %PYTHON_EXE% -m pip install PyQt5 pythonnet pywin32
    pause
)
