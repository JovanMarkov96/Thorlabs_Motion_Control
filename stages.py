"""
Thorlabs Stage Database
=======================

Comprehensive database of Thorlabs stages and actuators with their specifications.
This is the MASTER SOURCE for stage definitions. To add new stages, edit this file.

Data Structure
--------------
Each stage entry in the STAGES dictionary contains:

- **compatible_controllers** : List[str] - Controller types that can drive this stage
- **description** : str - Human-readable stage description
- **travel** : float - Total travel range in stage units
- **units** : str - Position units ('deg', 'mm', 'µm', or 'steps')
- **velocity_max** : float - Maximum velocity in units/second
- **acceleration_max** : float - Maximum acceleration in units/second²
- **jog_step_default** : float - Default jog step size
- **home_direction** : str - 'forward' or 'reverse' (if applicable)
- **encoder_counts_per_unit** : float - Encoder resolution (if applicable)

Stage Categories
----------------
Rotation Mounts (DC Servo - KDC101/TDC001):
    PRM1Z8, PRM1/MZ8, HDR50, K10CR1, DDR25, DDR100
    
Linear Stages (DC Servo - KDC101/TDC001):
    Z825B, Z812B, Z612B, MTS25, MTS50, LTS150, LTS300
    
Brushless DC Stages (KBD101):
    DDS100, DDS220, DDS300, DDS600, DDSM100
    
Piezo Inertial Actuators (KIM101):
    PIA13, PIA25, PIA50, PIAK10, PIAK25

Functions
---------
get_stage_info(stage_name) -> Dict
    Get full specifications for a stage.
    
get_compatible_stages(controller_type) -> List[str]
    Get list of stages compatible with a controller.
    
validate_stage_compatibility(controller_type, stage_name) -> bool
    Check if a stage is compatible with a controller.

Adding New Stages
-----------------
To add support for a new stage:

1. Add entry to STAGES dictionary with all required fields
2. Include in compatible_controllers list of supported controller types
3. Set appropriate travel, velocity, and encoder values from datasheet

Example::

    STAGES["MY_NEW_STAGE"] = {
        "compatible_controllers": ["KDC101"],
        "description": "My Custom Stage",
        "travel": 100.0,
        "units": "mm",
        "velocity_max": 10.0,
        "acceleration_max": 20.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 2048.0,
    }

Examples
--------
Look up stage specifications::

    from ThorlabsMotionControl.stages import get_stage_info
    
    prm = get_stage_info('PRM1Z8')
    print(f"Travel: {prm['travel']} {prm['units']}")
    print(f"Max velocity: {prm['velocity_max']} {prm['units']}/s")

Find compatible stages::

    from ThorlabsMotionControl.stages import get_compatible_stages
    
    kdc_stages = get_compatible_stages('KDC101')
    print(f"KDC101 supports: {', '.join(kdc_stages)}")
    
    kbd_stages = get_compatible_stages('KBD101')
    print(f"KBD101 supports: {', '.join(kbd_stages)}")

Author
------
Weizmann Institute Ion Trap Lab (Lab185)

Notes
-----
Stage specifications are based on Thorlabs product documentation.
Always verify with the latest Thorlabs datasheets for critical applications.
"""

from typing import Dict, List, Optional, Any

# ---------------------------------------------------------------------------
# Stage Definitions
# ---------------------------------------------------------------------------

STAGES: Dict[str, Dict[str, Any]] = {
    
    # =========================================================================
    # ROTATION MOUNTS (DC Servo) - KDC101 / TDC001
    # =========================================================================
    
    "PRM1Z8": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Motorized Rotation Mount, Ø1\" Optics, 360° Continuous",
        "travel": 360.0,
        "units": "deg",
        "continuous_rotation": True,
        "velocity_max": 25.0,  # deg/s
        "acceleration_max": 25.0,  # deg/s²
        "jog_step_default": 1.0,  # deg
        "home_direction": "reverse",
        "encoder_counts_per_unit": 1919.64,  # counts per degree
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 3x5",
        "notes": "For half-wave plates, quarter-wave plates, polarizers",
    },
    
    "PRM1/MZ8": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Motorized Rotation Mount, Ø1\" Optics, Magnetic Encoder",
        "travel": 360.0,
        "units": "deg",
        "continuous_rotation": True,
        "velocity_max": 25.0,
        "acceleration_max": 25.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 1919.64,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 3x5",
        "notes": "Magnetic encoder version of PRM1Z8",
    },
    
    "HDR50": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Heavy Duty Motorized Rotation Stage, 50mm Aperture",
        "travel": 360.0,
        "units": "deg",
        "continuous_rotation": True,
        "velocity_max": 20.0,
        "acceleration_max": 20.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 4096.0,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 3x5",
        "notes": "High load capacity rotation stage",
    },
    
    "K10CR1": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Motorized Rotation Mount, Cage System Compatible",
        "travel": 360.0,
        "units": "deg",
        "continuous_rotation": True,
        "velocity_max": 20.0,
        "acceleration_max": 20.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 2218.0,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 3x5",
        "notes": "30mm cage system compatible",
    },
    
    "DDR25": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Direct Drive Rotation Stage, 25mm Aperture",
        "travel": 360.0,
        "units": "deg",
        "continuous_rotation": True,
        "velocity_max": 180.0,
        "acceleration_max": 500.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 5555.56,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 3x5",
        "notes": "High speed, zero backlash",
    },
    
    "DDR100": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Direct Drive Rotation Stage, 100mm Aperture",
        "travel": 360.0,
        "units": "deg",
        "continuous_rotation": True,
        "velocity_max": 80.0,
        "acceleration_max": 200.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 5555.56,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 3x5",
        "notes": "Large aperture, high speed",
    },
    
    # =========================================================================
    # LINEAR STAGES (DC Servo) - KDC101 / TDC001
    # =========================================================================
    
    "Z825B": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Motorized Actuator, 25mm Travel",
        "travel": 25.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 2.3,  # mm/s
        "acceleration_max": 1.5,  # mm/s²
        "jog_step_default": 0.1,  # mm
        "home_direction": "reverse",
        "encoder_counts_per_unit": 34304.0,  # counts per mm
        "backlash_compensation": 0.012,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Standard 25mm actuator",
    },
    
    "Z812B": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Motorized Actuator, 12mm Travel",
        "travel": 12.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 2.3,
        "acceleration_max": 1.5,
        "jog_step_default": 0.1,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 34304.0,
        "backlash_compensation": 0.012,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Compact 12mm actuator",
    },
    
    "Z612B": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "Motorized Actuator, 6mm Travel",
        "travel": 6.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 2.3,
        "acceleration_max": 1.5,
        "jog_step_default": 0.05,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 34304.0,
        "backlash_compensation": 0.012,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Compact 6mm actuator",
    },
    
    "MTS25-Z8": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "25mm Motorized Translation Stage",
        "travel": 25.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 2.4,
        "acceleration_max": 3.0,
        "jog_step_default": 0.1,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 34555.0,
        "backlash_compensation": 0.02,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Integrated stage with Z8 motor",
    },
    
    "MTS50-Z8": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "50mm Motorized Translation Stage",
        "travel": 50.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 3.0,
        "acceleration_max": 4.5,
        "jog_step_default": 0.1,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 34555.0,
        "backlash_compensation": 0.02,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Integrated stage with Z8 motor",
    },
    
    "LTS150": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "150mm Long Travel Stage",
        "travel": 150.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 3.0,
        "acceleration_max": 2.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 409600.0,
        "backlash_compensation": 0.05,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Long travel, high precision",
    },
    
    "LTS300": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "300mm Long Travel Stage",
        "travel": 300.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 3.0,
        "acceleration_max": 2.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 409600.0,
        "backlash_compensation": 0.05,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Extended travel version",
    },
    
    "PT1-Z8": {
        "compatible_controllers": ["KDC101", "TDC001"],
        "description": "25mm Motorized Translation Stage (PT Series)",
        "travel": 25.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 2.6,
        "acceleration_max": 4.0,
        "jog_step_default": 0.1,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 34555.0,
        "backlash_compensation": 0.02,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "Standard 1\" travel stage",
    },
    
    # =========================================================================
    # BRUSHLESS DC STAGES - KBD101 Only
    # =========================================================================
    
    "DDS100": {
        "compatible_controllers": ["KBD101"],
        "description": "100mm Direct Drive Stage",
        "travel": 100.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 500.0,  # mm/s
        "acceleration_max": 5000.0,  # mm/s²
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 20000.0,
        "backlash_compensation": 0.0,  # No backlash - direct drive
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "High speed direct drive, requires phasing on first use",
    },
    
    "DDSM100": {
        "compatible_controllers": ["KBD101"],
        "description": "100mm Direct Drive Stage (M Series)",
        "travel": 100.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 500.0,  # mm/s
        "acceleration_max": 5000.0,  # mm/s²
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 20000.0,
        "backlash_compensation": 0.0,  # No backlash - direct drive
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "High speed direct drive, requires phasing on first use",
    },
    
    "DDS220": {
        "compatible_controllers": ["KBD101"],
        "description": "220mm Direct Drive Stage",
        "travel": 220.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 500.0,
        "acceleration_max": 5000.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 20000.0,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "High speed direct drive",
    },
    
    "DDS300": {
        "compatible_controllers": ["KBD101"],
        "description": "300mm Direct Drive Stage",
        "travel": 300.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 500.0,
        "acceleration_max": 5000.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 20000.0,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "High speed direct drive",
    },
    
    "DDS600": {
        "compatible_controllers": ["KBD101"],
        "description": "600mm Direct Drive Stage",
        "travel": 600.0,
        "units": "mm",
        "continuous_rotation": False,
        "velocity_max": 500.0,
        "acceleration_max": 5000.0,
        "jog_step_default": 1.0,
        "home_direction": "reverse",
        "encoder_counts_per_unit": 20000.0,
        "backlash_compensation": 0.0,
        "connector_type": "15-pin D-sub 2x7+1",
        "notes": "High speed direct drive, long travel",
    },
    
    # =========================================================================
    # PIEZO INERTIA ACTUATORS - KIM101 Only
    # =========================================================================
    
    "PIA13": {
        "compatible_controllers": ["KIM101"],
        "description": "Piezo Inertia Actuator, 13mm Travel",
        "travel": 13.0,
        "units": "mm",  # Note: controlled via steps, but travel is in mm
        "continuous_rotation": False,
        "step_size": 0.00002,  # 20nm per step minimum
        "step_rate_max": 2000,  # steps/second
        "step_acceleration_max": 100000,  # steps/s²
        "jog_step_default": 100,  # steps
        "home_direction": None,  # No traditional homing
        "encoder_counts_per_unit": None,  # No encoder
        "connector_type": "4-pin LEMO",
        "notes": "Open loop, step-based positioning. Use for mirror mounts (PIA-K10).",
    },
    
    "PIA25": {
        "compatible_controllers": ["KIM101"],
        "description": "Piezo Inertia Actuator, 25mm Travel",
        "travel": 25.0,
        "units": "mm",
        "continuous_rotation": False,
        "step_size": 0.00002,
        "step_rate_max": 2000,
        "step_acceleration_max": 100000,
        "jog_step_default": 100,
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "4-pin LEMO",
        "notes": "Open loop, extended travel version",
    },
    
    "PIA50": {
        "compatible_controllers": ["KIM101"],
        "description": "Piezo Inertia Actuator, 50mm Travel",
        "travel": 50.0,
        "units": "mm",
        "continuous_rotation": False,
        "step_size": 0.00002,
        "step_rate_max": 2000,
        "step_acceleration_max": 100000,
        "jog_step_default": 100,
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "4-pin LEMO",
        "notes": "Open loop, long travel version",
    },
    
    "PIAK10": {
        "compatible_controllers": ["KIM101"],
        "description": "Piezo Inertia Actuator for K10CR Mirror Mount",
        "travel": None,  # Angular, depends on mount
        "units": "steps",  # Pure step control
        "continuous_rotation": False,
        "step_size": 0.00002,
        "step_rate_max": 2000,
        "step_acceleration_max": 100000,
        "jog_step_default": 100,
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "4-pin LEMO",
        "notes": "For kinematic mirror mounts, X/Y tilt adjustment",
    },
    
    "PIAK25": {
        "compatible_controllers": ["KIM101"],
        "description": "Piezo Inertia Actuator for Larger Mirror Mounts",
        "travel": None,
        "units": "steps",
        "continuous_rotation": False,
        "step_size": 0.00002,
        "step_rate_max": 2000,
        "step_acceleration_max": 100000,
        "jog_step_default": 100,
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "4-pin LEMO",
        "notes": "Extended actuator for larger mirror mounts",
    },
    
    # =========================================================================
    # PIEZO STAGES (Voltage Controlled) - KPZ101 / TPZ001
    # =========================================================================
    
    "PK4FA7P1": {
        "compatible_controllers": ["KPZ101", "TPZ001"],
        "description": "Piezo Stack Actuator, 7µm Travel",
        "travel": 0.007,  # 7 µm
        "units": "mm",
        "continuous_rotation": False,
        "voltage_range": (0, 75),  # Volts
        "jog_step_default": 0.001,  # 1 µm
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "SMA",
        "notes": "Sub-micron positioning, voltage control",
    },
    
    "PAZ005": {
        "compatible_controllers": ["KPZ101", "TPZ001"],
        "description": "Amplified Piezo Actuator, 5µm Travel",
        "travel": 0.005,
        "units": "mm",
        "continuous_rotation": False,
        "voltage_range": (0, 75),
        "jog_step_default": 0.0005,
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "SMA",
        "notes": "High resolution positioning",
    },
    
    "PAZ015": {
        "compatible_controllers": ["KPZ101", "TPZ001"],
        "description": "Amplified Piezo Actuator, 15µm Travel",
        "travel": 0.015,
        "units": "mm",
        "continuous_rotation": False,
        "voltage_range": (0, 150),  # 150V version
        "jog_step_default": 0.001,
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "SMA",
        "notes": "Extended travel piezo",
    },
    
    "POLARIS-K1PZ": {
        "compatible_controllers": ["KPZ101", "TPZ001"],
        "description": "Piezo Mirror Mount, 1\" Optic",
        "travel": None,  # Angular
        "units": "V",  # Voltage control
        "continuous_rotation": False,
        "voltage_range": (0, 75),
        "jog_step_default": 1.0,  # Volts
        "home_direction": None,
        "encoder_counts_per_unit": None,
        "connector_type": "SMA",
        "notes": "Precision mirror steering",
    },
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_stage_info(stage_name: str) -> Optional[Dict[str, Any]]:
    """
    Get full stage information by name.
    
    Args:
        stage_name: Stage model name (e.g., "PRM1Z8")
        
    Returns:
        Stage info dict or None if unknown
    """
    return STAGES.get(stage_name)


def get_compatible_stages(controller_type: str) -> List[str]:
    """
    Get all stages compatible with a specific controller type.
    
    Args:
        controller_type: Controller type (e.g., "KDC101")
        
    Returns:
        List of compatible stage names
        
    Example:
        >>> get_compatible_stages("KIM101")
        ['PIA13', 'PIA25', 'PIA50', 'PIAK10', 'PIAK25']
    """
    return [
        name for name, info in STAGES.items()
        if controller_type in info["compatible_controllers"]
    ]


def get_all_stage_names() -> List[str]:
    """Return list of all known stage names."""
    return list(STAGES.keys())


def get_stages_by_units(units: str) -> List[str]:
    """
    Get all stages with specific position units.
    
    Args:
        units: One of "deg", "mm", "steps", "V"
        
    Returns:
        List of stage names
    """
    return [
        name for name, info in STAGES.items()
        if info["units"] == units
    ]


def is_rotation_stage(stage_name: str) -> bool:
    """Check if a stage is a rotation mount."""
    info = STAGES.get(stage_name)
    return info is not None and info.get("units") == "deg"


def is_inertial_stage(stage_name: str) -> bool:
    """Check if a stage is a piezo inertial actuator."""
    info = STAGES.get(stage_name)
    return info is not None and "KIM101" in info.get("compatible_controllers", [])


def get_default_jog_step(stage_name: str) -> float:
    """Get default jog step size for a stage."""
    info = STAGES.get(stage_name)
    return info["jog_step_default"] if info else 1.0


def get_stage_travel(stage_name: str) -> Optional[float]:
    """Get travel range for a stage (None for unlimited/angular)."""
    info = STAGES.get(stage_name)
    return info["travel"] if info else None
