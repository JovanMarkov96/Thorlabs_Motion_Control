"""
Device Manager for Thorlabs Motion Controllers
===============================================

This module provides the core device management functionality including:

- **Device Discovery**: USB enumeration of connected Thorlabs controllers
- **Controller Factory**: Automatic backend and controller type selection
- **Configuration Management**: Load/save device configurations from JSON
- **Stage Compatibility**: Validation and automatic stage detection

The module automatically selects between Kinesis .NET (64-bit Python) and
APT COM (32-bit Python) backends based on the runtime environment.

Functions
---------
discover_devices(use_kinesis_discovery=True) -> List[Dict]
    Discover all connected Thorlabs motion control devices.
    
create_controller(serial_number, controller_type=None, backend=None)
    Factory function to create appropriate controller instance.
    
load_device_config(serial_number) -> Dict
    Load saved configuration for a device.
    
save_device_config(serial_number, config) -> bool
    Save configuration for a device.
    
validate_stage_compatibility(controller_type, stage_name) -> bool
    Check if a stage is compatible with a controller.

Backend Detection
-----------------
kinesis_available() -> bool
    Check if Kinesis .NET DLLs and pythonnet are available.
    
apt_available() -> bool
    Check if APT COM is available.
    
get_available_backend() -> str
    Get the preferred available backend ('kinesis', 'apt', or 'none').

Stage Detection
---------------
detect_stage_for_device(serial_number, controller_type) -> Dict
    Detect the connected stage using Kinesis device settings.

Examples
--------
Basic device discovery::

    from ThorlabsMotionControl.device_manager import discover_devices
    
    devices = discover_devices()
    for dev in devices:
        print(f"{dev['controller_type']}: {dev['serial']}")

Creating a controller::

    from ThorlabsMotionControl import create_controller
    
    # Auto-detect everything
    ctrl = create_controller(27123456)
    
    # Specify controller type
    ctrl = create_controller(27123456, controller_type='KDC101')
    
    # Force specific backend
    ctrl = create_controller(27123456, backend='apt')

Configuration management::

    from ThorlabsMotionControl.device_manager import (
        save_device_config, load_device_config
    )
    
    # Save custom settings
    save_device_config(27123456, {
        'nickname': 'rotation_stage',
        'velocity': 10.0,
        'acceleration': 5.0
    })
    
    # Load settings
    config = load_device_config(27123456)

Requirements
------------
- **Kinesis Backend** (64-bit): 
  - 64-bit Python
  - pythonnet package
  - Thorlabs Kinesis installed at C:\\Program Files\\Thorlabs\\Kinesis
  
- **APT Backend** (32-bit):
  - 32-bit Python
  - comtypes package
  - Thorlabs APT software installed

Author
------
Weizmann Institute Ion Trap Lab (Lab185)
"""

from __future__ import annotations
import sys
import json
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from .controllers import (
    CONTROLLERS,
    get_controller_type,
    get_controller_info,
    get_channel_count,
    supports_apt,
)
from .stages import STAGES, get_stage_info, get_compatible_stages
from .base import MotorController, InertialController, PiezoController, ConfigurationError


# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------

# Default Kinesis installation path
KINESIS_PATH = Path(r"C:\Program Files\Thorlabs\Kinesis")

# Config file location (relative to this module)
CONFIG_DIR = Path(__file__).parent / "config"
DEVICES_JSON = CONFIG_DIR / "devices.json"


# ---------------------------------------------------------------------------
# Backend Detection
# ---------------------------------------------------------------------------

def is_64bit() -> bool:
    """Check if running 64-bit Python."""
    return struct.calcsize("P") * 8 == 64


def kinesis_available() -> bool:
    """Check if Kinesis .NET DLLs are available and pythonnet works."""
    if not is_64bit():
        return False
    
    if not KINESIS_PATH.exists():
        return False
    
    # Check for essential DLL
    device_manager_dll = KINESIS_PATH / "Thorlabs.MotionControl.DeviceManagerCLI.dll"
    if not device_manager_dll.exists():
        return False
    
    # Check if pythonnet (clr) can be imported
    try:
        import clr
        return True
    except ImportError:
        return False


def apt_available() -> bool:
    """Check if APT COM is available."""
    try:
        import comtypes.client as cc
        # Try to create system control
        ctrl = cc.CreateObject("MG17SYSTEM.MG17SystemCtrl.1")
        return True
    except Exception:
        return False


def get_available_backend() -> str:
    """
    Determine which backend to use.
    
    Returns:
        "kinesis" or "apt"
        
    Raises:
        RuntimeError if no backend available
    """
    if kinesis_available():
        return "kinesis"
    elif apt_available():
        return "apt"
    else:
        raise RuntimeError(
            "No Thorlabs backend available. "
            "Install Kinesis (64-bit Python) or APT (32-bit Python)."
        )


# ---------------------------------------------------------------------------
# Device Discovery
# ---------------------------------------------------------------------------

def discover_devices() -> List[Dict[str, Any]]:
    """
    Discover all connected Thorlabs motion controllers.
    
    Returns:
        List of dicts with keys:
            - serial: Serial number (int)
            - controller_type: e.g., "KDC101"
            - channels: Number of channels
            - description: Controller description
            - configured: Whether device is in devices.json
            
    Example:
        >>> devices = discover_devices()
        >>> for dev in devices:
        ...     print(f"{dev['serial']}: {dev['controller_type']}")
        27123456: KDC101
        97654321: KIM101
    """
    backend = get_available_backend()
    
    if backend == "kinesis":
        return _discover_kinesis()
    else:
        return _discover_apt()


def _discover_kinesis() -> List[Dict[str, Any]]:
    """Discover devices using Kinesis .NET."""
    devices = []
    
    try:
        # Add Kinesis path BEFORE importing clr
        kinesis_str = str(KINESIS_PATH)
        if kinesis_str not in sys.path:
            sys.path.insert(0, kinesis_str)
        
        import clr
        clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
        
        from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
        
        DeviceManagerCLI.BuildDeviceList()
        device_list = DeviceManagerCLI.GetDeviceList()
        
        # Load existing config to mark configured devices
        config = load_device_config()
        configured_serials = set(config.get("controllers", {}).keys())
        
        for serial_str in device_list:
            serial = int(serial_str)
            controller_type = get_controller_type(serial)
            
            if controller_type:
                info = get_controller_info(controller_type)
                devices.append({
                    "serial": serial,
                    "controller_type": controller_type,
                    "channels": info["channels"],
                    "description": info["description"],
                    "configured": str(serial) in configured_serials,
                })
    
    except Exception as e:
        print(f"Kinesis discovery error: {e}")
    
    return devices


def _discover_apt() -> List[Dict[str, Any]]:
    """Discover devices using APT COM."""
    devices = []
    
    try:
        import comtypes.client as cc
        
        system = cc.CreateObject("MG17SYSTEM.MG17SystemCtrl.1")
        system.StartCtrl()
        
        # Load existing config
        config = load_device_config()
        configured_serials = set(config.get("controllers", {}).keys())
        
        # Scan known hardware types
        hw_types = {
            27: "TDC001",
            29: "KPZ101",
            42: "KDC101",
            81: "TPZ001",
            # Note: KIM101 (97) and KBD101 (28) may not be in APT
        }
        
        for hw_type, controller_type in hw_types.items():
            try:
                count = system.GetNumHWUnitsEx(hw_type)
                for i in range(count):
                    serial = system.GetHWSerialNumEx(hw_type, i)
                    info = get_controller_info(controller_type)
                    
                    devices.append({
                        "serial": serial,
                        "controller_type": controller_type,
                        "channels": info["channels"],
                        "description": info["description"],
                        "configured": str(serial) in configured_serials,
                    })
            except Exception:
                continue
        
        system.StopCtrl()
    
    except Exception as e:
        print(f"APT discovery error: {e}")
    
    return devices


# ---------------------------------------------------------------------------
# Configuration Management
# ---------------------------------------------------------------------------

def load_device_config() -> Dict[str, Any]:
    """
    Load device configuration from devices.json.
    
    Returns:
        Configuration dict with "controllers" key mapping serial numbers
        to channel configurations.
    """
    if not DEVICES_JSON.exists():
        return {"_version": "1.0", "controllers": {}}
    
    try:
        with open(DEVICES_JSON, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load {DEVICES_JSON}: {e}")
        return {"_version": "1.0", "controllers": {}}


def save_device_config(config: Dict[str, Any]) -> bool:
    """
    Save device configuration to devices.json.
    
    Args:
        config: Configuration dict to save
        
    Returns:
        True if successful
    """
    try:
        # Ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(DEVICES_JSON, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


def get_device_channel_config(
    serial_number: int, 
    channel: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific device channel.
    
    Args:
        serial_number: Device serial number
        channel: Channel number (1-based)
        
    Returns:
        Channel config dict with stage, role, linked_group, or None
    """
    config = load_device_config()
    device_config = config.get("controllers", {}).get(str(serial_number), {})
    channels = device_config.get("channels", {})
    return channels.get(str(channel))


def set_device_channel_config(
    serial_number: int,
    channel: int,
    stage: Optional[str] = None,
    role: Optional[str] = None,
    linked_group: Optional[str] = None
) -> bool:
    """
    Set configuration for a specific device channel.
    
    Args:
        serial_number: Device serial number
        channel: Channel number (1-based)
        stage: Stage model name from stages.py
        role: User-defined role string (e.g., "674_hwp_rotation")
        linked_group: Group name for linked channels
        
    Returns:
        True if successful
    """
    config = load_device_config()
    
    serial_str = str(serial_number)
    if serial_str not in config.get("controllers", {}):
        config.setdefault("controllers", {})[serial_str] = {"channels": {}}
    
    channel_str = str(channel)
    config["controllers"][serial_str]["channels"][channel_str] = {
        "stage": stage,
        "role": role,
        "linked_group": linked_group,
    }
    
    return save_device_config(config)


def add_unconfigured_device(serial_number: int) -> bool:
    """
    Add a newly discovered device to config with empty channel configs.
    
    Args:
        serial_number: Device serial number
        
    Returns:
        True if successful
    """
    controller_type = get_controller_type(serial_number)
    if not controller_type:
        return False
    
    num_channels = get_channel_count(controller_type)
    
    config = load_device_config()
    serial_str = str(serial_number)
    
    if serial_str in config.get("controllers", {}):
        return True  # Already exists
    
    # Create empty channel configs
    channels = {}
    for ch in range(1, num_channels + 1):
        channels[str(ch)] = {
            "stage": None,
            "role": None,
            "linked_group": None,
        }
    
    config.setdefault("controllers", {})[serial_str] = {"channels": channels}
    return save_device_config(config)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_stage_compatibility(
    stage_name: str, 
    controller_type: str
) -> Tuple[bool, str]:
    """
    Validate that a stage is compatible with a controller.
    
    Args:
        stage_name: Stage model name
        controller_type: Controller type string
        
    Returns:
        Tuple of (is_valid, message)
        
    Example:
        >>> validate_stage_compatibility("PRM1Z8", "KDC101")
        (True, "PRM1Z8 is compatible with KDC101")
        
        >>> validate_stage_compatibility("PRM1Z8", "KIM101")
        (False, "PRM1Z8 requires KDC101 or TDC001, but controller is KIM101")
    """
    stage_info = get_stage_info(stage_name)
    
    if not stage_info:
        return False, f"Unknown stage: {stage_name}"
    
    compatible = stage_info["compatible_controllers"]
    
    if controller_type in compatible:
        return True, f"{stage_name} is compatible with {controller_type}"
    else:
        compatible_str = " or ".join(compatible)
        return False, f"{stage_name} requires {compatible_str}, but controller is {controller_type}"


def is_device_configured(serial_number: int) -> bool:
    """
    Check if a device has any configured channels.
    
    Returns:
        True if at least one channel has a stage assigned
    """
    config = load_device_config()
    device_config = config.get("controllers", {}).get(str(serial_number), {})
    channels = device_config.get("channels", {})
    
    for ch_config in channels.values():
        if ch_config and ch_config.get("stage"):
            return True
    return False


# ---------------------------------------------------------------------------
# Controller Factory
# ---------------------------------------------------------------------------

def create_controller(
    serial_number: int,
    channel: int = 1,
    backend: Optional[str] = None
) -> Union[MotorController, InertialController, PiezoController]:
    """
    Factory function to create appropriate controller instance.
    
    Args:
        serial_number: Device serial number
        channel: Channel number (1-based, for multi-channel devices)
        backend: Force "kinesis" or "apt" (auto-detect if None)
        
    Returns:
        Controller instance (type depends on device)
        
    Raises:
        ConfigurationError: If device type unknown or backend unavailable
        
    Example:
        >>> controller = create_controller(27123456)
        >>> controller.connect()
        >>> controller.home()
        >>> controller.move_absolute(45.0)
    """
    controller_type = get_controller_type(serial_number)
    
    if not controller_type:
        raise ConfigurationError(
            f"Unknown controller type for serial {serial_number}. "
            f"Serial prefix not recognized."
        )
    
    info = get_controller_info(controller_type)
    
    # Determine backend
    if backend is None:
        backend = get_available_backend()
    
    # Get channel config and stage info
    channel_config = get_device_channel_config(serial_number, channel)
    stage_config = None
    
    if channel_config and channel_config.get("stage"):
        stage_config = get_stage_info(channel_config["stage"])
        
        # Validate compatibility
        is_valid, msg = validate_stage_compatibility(
            channel_config["stage"], 
            controller_type
        )
        if not is_valid:
            print(f"Warning: {msg}")
    
    # Create controller instance
    if backend == "kinesis":
        controller = _create_kinesis_controller(
            serial_number, channel, controller_type, info
        )
    else:
        controller = _create_apt_controller(
            serial_number, channel, controller_type, info
        )
    
    # Apply stage configuration
    if stage_config:
        controller.configure_stage(stage_config)
    
    return controller


def _create_kinesis_controller(
    serial_number: int,
    channel: int,
    controller_type: str,
    info: Dict[str, Any]
) -> Union[MotorController, InertialController, PiezoController]:
    """Create Kinesis backend controller."""
    
    if controller_type == "KDC101":
        from .kinesis.kdc101 import KDC101Controller
        return KDC101Controller(serial_number, channel)
    
    elif controller_type == "KBD101":
        from .kinesis.kbd101 import KBD101Controller
        return KBD101Controller(serial_number, channel)
    
    elif controller_type == "TDC001":
        from .kinesis.tdc001 import TDC001Controller
        return TDC001Controller(serial_number, channel)
    
    elif controller_type == "KIM101":
        from .kinesis.kim101 import KIM101Controller
        return KIM101Controller(serial_number, channel)
    
    elif controller_type in ("KPZ101", "TPZ001"):
        from .kinesis.kpz101 import KPZ101Controller
        return KPZ101Controller(serial_number, channel)
    
    else:
        raise ConfigurationError(f"No Kinesis backend for {controller_type}")


def _create_apt_controller(
    serial_number: int,
    channel: int,
    controller_type: str,
    info: Dict[str, Any]
) -> Union[MotorController, InertialController, PiezoController]:
    """Create APT COM backend controller."""
    
    if not supports_apt(controller_type):
        raise ConfigurationError(
            f"{controller_type} does not support APT COM interface. "
            f"Use 64-bit Python with Kinesis instead."
        )
    
    motor_type = info["motor_type"]
    
    if motor_type in ("dc_servo", "brushless"):
        from .apt.motor import APTMotorAdapter
        return APTMotorAdapter(serial_number, channel, info["apt_hw_type"])
    
    elif motor_type == "piezo":
        from .apt.piezo import APTPiezoAdapter
        return APTPiezoAdapter(serial_number, channel)
    
    else:
        raise ConfigurationError(f"No APT backend for motor type: {motor_type}")


# ---------------------------------------------------------------------------
# Linked Group Helpers
# ---------------------------------------------------------------------------

def get_linked_channels(
    serial_number: int, 
    linked_group: str
) -> List[int]:
    """
    Get all channels in a linked group for a device.
    
    Args:
        serial_number: Device serial number
        linked_group: Group name
        
    Returns:
        List of channel numbers in the group
    """
    config = load_device_config()
    device_config = config.get("controllers", {}).get(str(serial_number), {})
    channels = device_config.get("channels", {})
    
    result = []
    for ch_str, ch_config in channels.items():
        if ch_config and ch_config.get("linked_group") == linked_group:
            result.append(int(ch_str))
    
    return sorted(result)


def get_all_linked_groups() -> Dict[str, List[Tuple[int, int]]]:
    """
    Get all linked groups across all devices.
    
    Returns:
        Dict mapping group name to list of (serial, channel) tuples
    """
    config = load_device_config()
    groups: Dict[str, List[Tuple[int, int]]] = {}
    
    for serial_str, device_config in config.get("controllers", {}).items():
        serial = int(serial_str)
        channels = device_config.get("channels", {})
        
        for ch_str, ch_config in channels.items():
            if ch_config:
                group = ch_config.get("linked_group")
                if group:
                    groups.setdefault(group, []).append((serial, int(ch_str)))
    
    return groups


# ---------------------------------------------------------------------------
# Stage Auto-Detection (Motor EEPROM Query)
# ---------------------------------------------------------------------------

def get_connected_stage_info(
    serial_number: int, 
    controller_type: str
) -> Optional[Dict[str, Any]]:
    """
    Query the motor EEPROM to detect connected stage.
    
    This connects to the controller, reads the stage definition from the
    motor's EEPROM, then disconnects. Works for motor controllers like
    KDC101, KBD101, TDC001.
    
    Args:
        serial_number: Device serial number
        controller_type: Controller type (KDC101, KBD101, TDC001)
        
    Returns:
        Dict with stage info or None if no stage connected:
            - part_number: Stage model (e.g., "DDS100", "PRM1Z8")
            - serial_number: Stage serial number
            - stage_id: Internal stage ID
    """
    backend = get_available_backend()
    
    if backend != "kinesis":
        # APT doesn't have GetStageDefinition
        return None
    
    # Only motor controllers support stage detection
    if controller_type not in ("KDC101", "KBD101", "TDC001"):
        return None
    
    try:
        return _get_stage_info_kinesis(serial_number, controller_type)
    except Exception as e:
        print(f"Stage detection failed for {serial_number}: {e}")
        return None


def _get_stage_info_kinesis(
    serial_number: int, 
    controller_type: str
) -> Optional[Dict[str, Any]]:
    """Internal: Query stage info via Kinesis .NET."""
    import time
    
    # Add Kinesis path
    kinesis_str = str(KINESIS_PATH)
    if kinesis_str not in sys.path:
        sys.path.insert(0, kinesis_str)
    
    import clr
    clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
    
    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
    DeviceManagerCLI.BuildDeviceList()
    
    serial_str = str(serial_number)
    device = None
    
    try:
        # Create device based on controller type
        if controller_type == "KDC101":
            clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
            from Thorlabs.MotionControl.KCube.DCServoCLI import KCubeDCServo
            device = KCubeDCServo.CreateKCubeDCServo(serial_str)
        elif controller_type == "KBD101":
            clr.AddReference("Thorlabs.MotionControl.KCube.BrushlessMotorCLI")
            from Thorlabs.MotionControl.KCube.BrushlessMotorCLI import KCubeBrushlessMotor
            device = KCubeBrushlessMotor.CreateKCubeBrushlessMotor(serial_str)
        elif controller_type == "TDC001":
            clr.AddReference("Thorlabs.MotionControl.TCube.DCServoCLI")
            from Thorlabs.MotionControl.TCube.DCServoCLI import TCubeDCServo
            device = TCubeDCServo.CreateTCubeDCServo(serial_str)
        else:
            return None
        
        if device is None:
            return None
        
        # Connect briefly to query stage
        device.Connect(serial_str)
        time.sleep(0.3)
        
        # Load config to initialize stage settings
        device.LoadMotorConfiguration(serial_str)
        device.StartPolling(250)
        time.sleep(0.3)
        
        # Get stage definition from motor EEPROM
        stage_def = device.GetStageDefinition()
        
        result = None
        if stage_def and stage_def.PartNumber:
            result = {
                "part_number": str(stage_def.PartNumber).strip(),
                "serial_number": str(stage_def.SerialNumber).strip() if stage_def.SerialNumber else None,
                "stage_id": int(stage_def.StageID) if stage_def.StageID else None,
            }
        
        # Cleanup
        device.StopPolling()
        device.Disconnect()
        
        return result
    
    except Exception as e:
        # Ensure cleanup on error
        if device:
            try:
                device.StopPolling()
                device.Disconnect()
            except:
                pass
        raise


def discover_devices_with_stages() -> List[Dict[str, Any]]:
    """
    Discover all devices AND auto-detect connected stages.
    
    This is an enhanced version of discover_devices() that also queries
    motor controllers to detect connected stages from motor EEPROM.
    
    Returns:
        List of device dicts (same as discover_devices) plus:
            - stage: Dict with part_number, serial_number, stage_id (or None)
            - stage_params: Full stage parameters from database (or None)
            
    Example:
        >>> devices = discover_devices_with_stages()
        >>> for dev in devices:
        ...     print(f"{dev['serial']}: {dev['controller_type']}")
        ...     if dev.get('stage'):
        ...         print(f"  Stage: {dev['stage']['part_number']}")
    """
    # Get basic device list
    devices = discover_devices()
    
    # Motor controllers that support stage detection
    motor_controllers = {"KDC101", "KBD101", "TDC001"}
    
    for dev in devices:
        if dev["controller_type"] in motor_controllers:
            # Query connected stage
            stage_info = get_connected_stage_info(
                dev["serial"], 
                dev["controller_type"]
            )
            
            dev["stage"] = stage_info
            
            # Look up stage parameters in database
            if stage_info and stage_info.get("part_number"):
                dev["stage_params"] = get_stage_info(stage_info["part_number"])
            else:
                dev["stage_params"] = None
        else:
            # Non-motor controllers (KIM101, KPZ101) don't have motorized stages
            dev["stage"] = None
            dev["stage_params"] = None
    
    return devices
