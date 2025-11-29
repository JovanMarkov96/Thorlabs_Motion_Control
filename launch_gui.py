#!/usr/bin/env python
"""
Thorlabs Motion Control GUI Launcher

Simple script to launch the Thorlabs Motion Control GUI application.
Double-click this file or run from command line:

    python launch_gui.py

Requirements:
    - Python 3.8+
    - PyQt5
    - pythonnet
    - Thorlabs Kinesis installed
"""

import sys
import os

# Add parent directory to path so imports work when running directly
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(script_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def main():
    """Launch the Thorlabs Motion Control GUI."""
    try:
        from Hardware.Thorlabs_Motion_Control.gui import main as gui_main
        gui_main()
    except ImportError as e:
        # Try alternative import path (when running from repo root)
        try:
            from gui import main as gui_main
            gui_main()
        except ImportError:
            print(f"Error: Could not import GUI module: {e}")
            print("\nMake sure you have installed the required dependencies:")
            print("  pip install PyQt5 pythonnet pywin32")
            print("\nAnd that Thorlabs Kinesis is installed.")
            sys.exit(1)

if __name__ == "__main__":
    main()
