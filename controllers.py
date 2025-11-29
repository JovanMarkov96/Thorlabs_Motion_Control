"""
Thorlabs Controller Registry
============================

This module defines all supported Thorlabs motion controllers with their
hardware characteristics, capabilities, and backend configuration.

Data Structure
--------------
The CONTROLLERS dictionary maps controller model names to configuration dicts
containing:

- **prefix** : int - Serial number prefix (e.g., 27 for KDC101)
- **channels** : int - Number of channels (1 for most, 4 for KIM101)
- **motor_type** : str - 'dc_servo', 'brushless', 'inertial', or 'piezo'
- **description** : str - Human-readable controller description
- **kinesis_dll** : str - Kinesis .NET DLL name
- **kinesis_class** : str - Kinesis controller class name
- **apt_hw_type** : int or None - APT hardware type code
- **apt_progid** : str or None - APT COM ProgID
- **supports_homing** : bool - Whether controller supports homing
- **supports_position** : bool - Whether controller has position feedback

Supported Controllers
---------------------
========  ======  ========  ========================================
Model     Prefix  Channels  Description
========  ======  ========  ========================================
KDC101    27      1         K-Cube DC Servo Motor Driver
KBD101    28      1         K-Cube Brushless DC Motor Driver
TDC001    83      1         T-Cube DC Servo Motor Driver (Legacy)
KIM101    97      4         K-Cube Piezo Inertial Motor Driver
KPZ101    29      1         K-Cube Piezo Driver
========  ======  ========  ========================================

Functions
---------
get_controller_type(serial_number) -> str
    Determine controller type from serial number prefix.
    
get_controller_info(controller_type) -> Dict
    Get full configuration for a controller type.
    
get_channel_count(controller_type) -> int
    Get number of channels for a controller.
    
supports_apt(controller_type) -> bool
    Check if controller has APT COM support.

Examples
--------
Look up controller type::

    from ThorlabsMotionControl.controllers import get_controller_type
    
    ctrl_type = get_controller_type(27123456)  # Returns 'KDC101'
    ctrl_type = get_controller_type(97000001)  # Returns 'KIM101'

Get controller capabilities::

    from ThorlabsMotionControl.controllers import (
        get_controller_info, supports_apt
    )
    
    info = get_controller_info('KDC101')
    print(f"Max velocity: {info['max_velocity']}")
    print(f"APT support: {supports_apt('KDC101')}")  # True
    print(f"APT support: {supports_apt('KIM101')}")  # False

Author
------
Weizmann Institute Ion Trap Lab (Lab185)
"""

from typing import Dict, List, Optional, Any

# ---------------------------------------------------------------------------
# Controller Definitions
# ---------------------------------------------------------------------------

CONTROLLERS: Dict[str, Dict[str, Any]] = {
    # K-Cube DC Servo Motor Driver
    "KDC101": {
        "prefix": 27,
        "channels": 1,
        "motor_type": "dc_servo",
        "description": "K-Cube DC Servo Motor Driver",
        "kinesis_dll": "Thorlabs.MotionControl.KCube.DCServoCLI",
        "kinesis_class": "KCubeDCServo",
        "apt_hw_type": 42,
        "apt_progid": "MGMOTOR.MGMotorCtrl.1",
        "supports_homing": True,
        "supports_position": True,
        "max_velocity": 2.6,  # mm/s or deg/s depending on stage
        "max_acceleration": 4.0,
    },
    
    # K-Cube Brushless DC Motor Driver
    "KBD101": {
        "prefix": 28,
        "channels": 1,
        "motor_type": "brushless",
        "description": "K-Cube Brushless DC Motor Driver",
        "kinesis_dll": "Thorlabs.MotionControl.KCube.BrushlessMotorCLI",
        "kinesis_class": "KCubeBrushlessMotor",
        "apt_hw_type": None,  # No APT support for brushless
        "apt_progid": None,
        "supports_homing": True,
        "supports_position": True,
        "max_velocity": 500.0,  # mm/s with DDS stages
        "max_acceleration": 1000.0,
    },
    
    # T-Cube DC Servo Motor Driver (legacy)
    "TDC001": {
        "prefix": 83,
        "channels": 1,
        "motor_type": "dc_servo",
        "description": "T-Cube DC Servo Motor Driver (Legacy)",
        "kinesis_dll": "Thorlabs.MotionControl.TCube.DCServoCLI",
        "kinesis_class": "TCubeDCServo",
        "apt_hw_type": 27,
        "apt_progid": "MGMOTOR.MGMotorCtrl.1",
        "supports_homing": True,
        "supports_position": True,
        "max_velocity": 2.6,
        "max_acceleration": 4.0,
    },
    
    # K-Cube Inertial Motor Driver (4-channel, for PIA actuators)
    "KIM101": {
        "prefix": 97,
        "channels": 4,
        "motor_type": "inertial",
        "description": "K-Cube Inertial Motor Driver (4-channel)",
        "kinesis_dll": "Thorlabs.MotionControl.KCube.InertialMotorCLI",
        "kinesis_class": "KCubeInertialMotor",
        "apt_hw_type": None,  # Inertial motors use different protocol
        "apt_progid": None,
        "supports_homing": False,  # Inertial motors don't home traditionally
        "supports_position": False,  # Step-based, no absolute position
        "max_step_rate": 2000,  # steps/second
        "max_step_acceleration": 100000,  # steps/s²
    },
    
    # K-Cube Piezo Driver
    "KPZ101": {
        "prefix": 29,
        "channels": 1,
        "motor_type": "piezo",
        "description": "K-Cube Piezo Driver",
        "kinesis_dll": "Thorlabs.MotionControl.KCube.PiezoCLI",
        "kinesis_class": "KCubePiezo",
        "apt_hw_type": 29,
        "apt_progid": "APTPZMOTOR.APTPZMotorCtrl.1",
        "supports_homing": False,
        "supports_position": True,  # With strain gauge feedback
        "voltage_range": (0, 75),  # Default, can be 0-150V
    },
    
    # T-Cube Piezo Driver (legacy)
    "TPZ001": {
        "prefix": 81,
        "channels": 1,
        "motor_type": "piezo",
        "description": "T-Cube Piezo Driver (Legacy)",
        "kinesis_dll": "Thorlabs.MotionControl.TCube.PiezoCLI",
        "kinesis_class": "TCubePiezo",
        "apt_hw_type": 81,
        "apt_progid": "APTPZMOTOR.APTPZMotorCtrl.1",
        "supports_homing": False,
        "supports_position": True,
        "voltage_range": (0, 75),
    },
}

# Serial prefix to controller type lookup
_PREFIX_TO_CONTROLLER: Dict[int, str] = {
    info["prefix"]: name for name, info in CONTROLLERS.items()
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_controller_type(serial_number: int) -> Optional[str]:
    """
    Determine controller type from serial number prefix.
    
    Args:
        serial_number: Device serial number (e.g., 27123456)
        
    Returns:
        Controller type string (e.g., "KDC101") or None if unknown
        
    Example:
        >>> get_controller_type(27123456)
        'KDC101'
        >>> get_controller_type(97654321)
        'KIM101'
    """
    # Extract first 2 digits as prefix
    prefix = int(str(serial_number)[:2])
    return _PREFIX_TO_CONTROLLER.get(prefix)


def get_controller_info(controller_type: str) -> Optional[Dict[str, Any]]:
    """
    Get full controller information by type name.
    
    Args:
        controller_type: Controller type string (e.g., "KDC101")
        
    Returns:
        Controller info dict or None if unknown
    """
    return CONTROLLERS.get(controller_type)


def get_all_controller_types() -> List[str]:
    """Return list of all supported controller type names."""
    return list(CONTROLLERS.keys())


def get_controllers_by_motor_type(motor_type: str) -> List[str]:
    """
    Get all controllers that support a specific motor type.
    
    Args:
        motor_type: One of "dc_servo", "brushless", "inertial", "piezo"
        
    Returns:
        List of controller type names
    """
    return [
        name for name, info in CONTROLLERS.items()
        if info["motor_type"] == motor_type
    ]


def supports_apt(controller_type: str) -> bool:
    """Check if a controller type supports APT COM interface."""
    info = CONTROLLERS.get(controller_type)
    return info is not None and info.get("apt_hw_type") is not None


def get_channel_count(controller_type: str) -> int:
    """Get number of channels for a controller type."""
    info = CONTROLLERS.get(controller_type)
    return info["channels"] if info else 1
