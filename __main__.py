"""
Thorlabs Motion Control - Module Entry Point

Allows running the GUI with:
    python -m ThorlabsMotionControl
"""

# IMPORTANT: Pre-initialize pythonnet BEFORE any other imports
import sys
from pathlib import Path

_kinesis_path = Path(r"C:\Program Files\Thorlabs\Kinesis")
if _kinesis_path.exists():
    kinesis_str = str(_kinesis_path)
    if kinesis_str not in sys.path:
        sys.path.insert(0, kinesis_str)
    try:
        import clr
    except ImportError:
        pass

from .gui import main

if __name__ == "__main__":
    main()
