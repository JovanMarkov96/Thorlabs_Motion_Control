@echo off
REM Thorlabs Motion Control GUI Launcher
REM Double-click this file to launch the GUI

cd /d "%~dp0"
python launch_gui.py

if errorlevel 1 (
    echo.
    echo Failed to launch GUI. Make sure Python and dependencies are installed.
    echo Required: pip install PyQt5 pythonnet pywin32
    pause
)
