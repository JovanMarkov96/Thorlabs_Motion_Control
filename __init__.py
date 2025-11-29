"""
Thorlabs Motion Control Package
===============================

A unified Python interface for controlling Thorlabs motorized stages and actuators
via Kinesis .NET (64-bit) or APT COM (32-bit fallback).

This package provides a consistent API across different Thorlabs controller families,
automatic stage detection, device discovery, and a graphical user interface.

Features
--------
- **Unified API**: Consistent interface across all controller types
- **Auto-Detection**: Automatic stage and actuator detection
- **Device Discovery**: USB enumeration of all connected Thorlabs devices
- **Multi-Backend**: Kinesis .NET (primary) with APT COM fallback
- **Type Safety**: Full type hints and validation
- **GUI Support**: Built-in Qt-based graphical interface

Supported Controllers
---------------------
DC Servo Controllers:
    - **KDC101**: K-Cube DC Servo Motor Driver (USB, compact)
    - **TDC001**: T-Cube DC Servo Motor Driver (USB, legacy)

Brushless DC Controllers:
    - **KBD101**: K-Cube Brushless DC Motor Driver (high-precision stages)

Piezo Controllers:
    - **KPZ101**: K-Cube Piezo Driver (voltage-controlled)
    - **KIM101**: K-Cube Piezo Inertial Motor Driver (4-channel, stick-slip)

Supported Stages/Actuators
--------------------------
Rotation Mounts (DC Servo):
    PRM1Z8, HDR50, K10CR1, DDR25, DDR100

Linear Stages (DC Servo):
    Z825B, Z812B, MTS25, MTS50, LTS150, LTS300

Brushless DC Stages:
    DDS100, DDS220, DDS300, DDS600, DDSM100

Piezo Inertial Actuators:
    PIA13, PIA25, PIA50, PIAK10, PIAK25

Quick Start
-----------
Device Discovery::

    from ThorlabsMotionControl import discover_devices
    
    devices = discover_devices()
    for dev in devices:
        print(f"{dev['serial']}: {dev['controller_type']}")

Creating a Controller::

    from ThorlabsMotionControl import create_controller
    
    # Auto-detect controller type from serial number
    controller = create_controller(serial_number=27123456)
    controller.connect()
    controller.home()
    controller.move_absolute(45.0)  # degrees for rotation mount
    controller.disconnect()

Using Base Classes::

    from ThorlabsMotionControl import MotorController, InertialController
    
    # Type hints for function signatures
    def process_motor(motor: MotorController) -> None:
        motor.home()
        motor.move_absolute(10.0)

GUI Launch
----------
From command line::

    python -m ThorlabsMotionControl.gui

From Python::

    from ThorlabsMotionControl import launch_gui
    launch_gui()

Requirements
------------
- Python 3.8+
- pythonnet (for Kinesis .NET backend)
- Thorlabs Kinesis software (v1.14+)
- PyQt6 (for GUI, optional)

Installation
------------
::

    pip install pythonnet
    # Ensure Thorlabs Kinesis is installed at C:\\Program Files\\Thorlabs\\Kinesis

Package Structure
-----------------
::

    ThorlabsMotionControl/
    ├── __init__.py      # Package exports and documentation
    ├── base.py          # Abstract base classes
    ├── controllers.py   # Controller registry and metadata
    ├── stages.py        # Stage registry and compatibility
    ├── device_manager.py # Device discovery and factory
    ├── gui.py           # Qt-based GUI
    ├── kinesis/         # Kinesis .NET implementations
    │   ├── kdc101.py    # KDC101 controller
    │   ├── kbd101.py    # KBD101 controller
    │   ├── tdc001.py    # TDC001 controller
    │   ├── kim101.py    # KIM101 controller
    │   └── kpz101.py    # KPZ101 controller
    ├── apt/             # APT COM fallback implementations
    │   ├── motor.py     # Motor controllers
    │   └── piezo.py     # Piezo controllers
    ├── config/          # Configuration files
    │   └── devices.json # Device configurations
    └── tests/           # Comprehensive test suites
        ├── run_all_tests.py
        ├── test_kdc101.py
        ├── test_kbd101.py
        ├── test_tdc001.py
        └── test_kim101.py

Author
------
Weizmann Institute Ion Trap Lab (Lab185)

License
-------
MIT License

See Also
--------
- README.md : Detailed documentation and examples
- CONTRIBUTING.md : Contribution guidelines
- tests/README.md : Test suite documentation
"""

__version__ = "1.0.0"
__author__ = "Lab185"

# Import registries
from .controllers import CONTROLLERS, get_controller_type, get_controller_info
from .stages import STAGES, get_stage_info, get_compatible_stages

# Import device management
from .device_manager import (
    discover_devices,
    create_controller,
    load_device_config,
    save_device_config,
    validate_stage_compatibility,
)

# Import base classes for type hints and subclassing
from .base import MotorController, InertialController, PiezoController

# GUI entry point
def launch_gui():
    """Launch the Thorlabs Motion Control GUI."""
    from .gui import main
    main()

__all__ = [
    # Version
    "__version__",
    # Registries
    "CONTROLLERS",
    "STAGES",
    "get_controller_type",
    "get_controller_info",
    "get_stage_info",
    "get_compatible_stages",
    # Device management
    "discover_devices",
    "create_controller",
    "load_device_config",
    "save_device_config",
    "validate_stage_compatibility",
    # Base classes
    "MotorController",
    "InertialController",
    "PiezoController",
    # GUI
    "launch_gui",
]
