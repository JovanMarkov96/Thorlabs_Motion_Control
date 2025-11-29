"""
Abstract Base Classes for Thorlabs Motion Controllers
======================================================

This module defines the abstract interfaces that all controller backends
(Kinesis .NET, APT COM) must implement. It provides three main base classes:

Classes
-------
MotorController
    Abstract base for DC servo and brushless motor controllers.
    Implementations: KDC101, KBD101, TDC001, APTMotorAdapter
    
InertialController
    Abstract base for piezo inertial motor controllers.
    Extends MotorController with step-based movement.
    Implementations: KIM101
    
PiezoController
    Abstract base for piezo voltage controllers.
    Implementations: KPZ101, APTPiezoAdapter

Enums
-----
ControllerState
    Connection and motion state enumeration.

Exceptions
----------
MotionControlError
    Base exception for all motion control errors.
ConnectionError
    Failed to establish device connection.
CommunicationError
    Communication error during operation.
MovementError
    Error during movement (limit, timeout, etc.).
ConfigurationError
    Invalid configuration or incompatible hardware.

Design Pattern
--------------
The base classes implement the Template Method pattern, where the
abstract methods define the interface and concrete implementations
provide hardware-specific behavior. All controllers support:

- Context manager protocol (``with`` statement)
- Callback registration for state/position updates
- Stage configuration injection
- Common state tracking

Example
-------
Creating a custom controller implementation::

    from ThorlabsMotionControl.base import MotorController
    
    class MyController(MotorController):
        def connect(self) -> bool:
            # Hardware-specific connection
            ...
        
        def disconnect(self) -> None:
            # Hardware-specific disconnection
            ...
        
        # ... implement other abstract methods

Using context manager::

    with create_controller(27123456) as ctrl:
        ctrl.home()
        ctrl.move_absolute(45.0)
    # Auto-disconnects on exit

Author
------
Weizmann Institute Ion Trap Lab (Lab185)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from enum import Enum


class ControllerState(Enum):
    """Controller connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    HOMING = "homing"
    MOVING = "moving"
    ERROR = "error"


class MotorController(ABC):
    """
    Abstract base class for DC servo and brushless motor controllers.
    
    Implementations: KDC101, KBD101, TDC001 (Kinesis), APTMotorAdapter (APT)
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        """
        Initialize controller.
        
        Args:
            serial_number: Device serial number
            channel: Channel number (1 for single-channel devices)
        """
        self.serial_number = serial_number
        self.channel = channel
        self.state = ControllerState.DISCONNECTED
        self._stage_config: Optional[Dict[str, Any]] = None
        self._on_state_change: Optional[Callable[[ControllerState], None]] = None
        self._on_position_change: Optional[Callable[[float], None]] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if controller is connected."""
        return self.state in (
            ControllerState.CONNECTED, 
            ControllerState.HOMING, 
            ControllerState.MOVING
        )
    
    @property
    def is_moving(self) -> bool:
        """Check if stage is currently moving."""
        return self.state == ControllerState.MOVING
    
    def configure_stage(self, stage_config: Dict[str, Any]) -> None:
        """
        Configure controller for a specific stage.
        
        Args:
            stage_config: Stage configuration from stages.py
        """
        self._stage_config = stage_config
    
    def set_callbacks(
        self,
        on_state_change: Optional[Callable[[ControllerState], None]] = None,
        on_position_change: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        Set callback functions for state and position updates.
        
        Args:
            on_state_change: Called when controller state changes
            on_position_change: Called when position changes
        """
        self._on_state_change = on_state_change
        self._on_position_change = on_position_change
    
    def _set_state(self, new_state: ControllerState) -> None:
        """Update state and notify callback."""
        self.state = new_state
        if self._on_state_change:
            self._on_state_change(new_state)
    
    # -------------------------------------------------------------------------
    # Abstract Methods - Must be implemented by subclasses
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the controller.
        
        Returns:
            True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the controller."""
        pass
    
    @abstractmethod
    def identify(self) -> None:
        """Flash the controller's front panel LED for identification."""
        pass
    
    @abstractmethod
    def home(self, wait: bool = True, timeout: float = 60.0) -> bool:
        """
        Home the stage.
        
        Args:
            wait: If True, block until homing completes
            timeout: Maximum time to wait (seconds)
            
        Returns:
            True if homing successful
        """
        pass
    
    @abstractmethod
    def move_absolute(
        self, 
        position: float, 
        wait: bool = True, 
        timeout: float = 60.0
    ) -> bool:
        """
        Move to an absolute position.
        
        Args:
            position: Target position in stage units (mm, deg)
            wait: If True, block until move completes
            timeout: Maximum time to wait (seconds)
            
        Returns:
            True if move successful
        """
        pass
    
    @abstractmethod
    def move_relative(
        self, 
        distance: float, 
        wait: bool = True, 
        timeout: float = 60.0
    ) -> bool:
        """
        Move by a relative distance.
        
        Args:
            distance: Distance to move in stage units
            wait: If True, block until move completes
            timeout: Maximum time to wait (seconds)
            
        Returns:
            True if move successful
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop any ongoing movement immediately."""
        pass
    
    @abstractmethod
    def get_position(self) -> float:
        """
        Get current position.
        
        Returns:
            Current position in stage units
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information.
        
        Returns:
            Dict with keys: position, velocity, is_homed, is_moving, error, etc.
        """
        pass
    
    # -------------------------------------------------------------------------
    # Optional Methods - Override if supported
    # -------------------------------------------------------------------------
    
    def set_velocity(self, velocity: float) -> bool:
        """
        Set maximum velocity.
        
        Args:
            velocity: Velocity in stage units/second
            
        Returns:
            True if successful
        """
        return False
    
    def set_acceleration(self, acceleration: float) -> bool:
        """
        Set acceleration.
        
        Args:
            acceleration: Acceleration in stage units/second²
            
        Returns:
            True if successful
        """
        return False
    
    def get_velocity_params(self) -> Dict[str, float]:
        """
        Get velocity parameters.
        
        Returns:
            Dict with max_velocity, acceleration
        """
        return {"max_velocity": 0, "acceleration": 0}
    
    def is_homed(self) -> bool:
        """Check if stage has been homed."""
        return False
    
    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *args):
        self.disconnect()


class InertialController(MotorController):
    """
    Abstract base class for piezo inertial motor controllers (KIM101).
    
    Inertial motors work via step pulses rather than position commands.
    They do not have encoders and cannot home traditionally.
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        super().__init__(serial_number, channel)
        self._step_count = 0  # Track steps internally
    
    # Override: Inertial motors don't support traditional homing
    def home(self, wait: bool = True, timeout: float = 60.0) -> bool:
        """
        Inertial motors do not support traditional homing.
        This moves to the physical limit (use with caution).
        
        Returns:
            False - use jog_to_limit() instead for intentional limit seeking
        """
        return False
    
    # Override: Position is estimated from steps
    def get_position(self) -> float:
        """
        Get estimated position based on step count.
        
        Note: Inertial motors are open-loop; position is approximate.
        """
        if self._stage_config:
            step_size = self._stage_config.get("step_size", 0.00002)
            return self._step_count * step_size
        return float(self._step_count)
    
    # -------------------------------------------------------------------------
    # Inertial-Specific Abstract Methods
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def jog(self, direction: int, steps: int = 1) -> bool:
        """
        Jog the actuator by a number of steps.
        
        Args:
            direction: 1 for forward, -1 for reverse
            steps: Number of steps to move
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def jog_continuous(self, direction: int) -> bool:
        """
        Start continuous jogging.
        
        Args:
            direction: 1 for forward, -1 for reverse
            
        Returns:
            True if started successfully
        """
        pass
    
    @abstractmethod
    def set_step_rate(self, rate: int) -> bool:
        """
        Set step rate (steps per second).
        
        Args:
            rate: Step rate (typically 1-2000)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def set_step_acceleration(self, acceleration: int) -> bool:
        """
        Set step acceleration.
        
        Args:
            acceleration: Steps/second²
            
        Returns:
            True if successful
        """
        pass
    
    def reset_step_count(self) -> None:
        """Reset internal step counter to zero."""
        self._step_count = 0
    
    # -------------------------------------------------------------------------
    # Implement move_* using steps
    # -------------------------------------------------------------------------
    
    def move_absolute(
        self, 
        position: float, 
        wait: bool = True, 
        timeout: float = 60.0
    ) -> bool:
        """
        Move to approximate absolute position.
        
        Note: Inertial motors are open-loop; accuracy depends on step size.
        """
        current = self.get_position()
        distance = position - current
        return self.move_relative(distance, wait, timeout)
    
    def move_relative(
        self, 
        distance: float, 
        wait: bool = True, 
        timeout: float = 60.0
    ) -> bool:
        """
        Move by a relative distance.
        
        Converts distance to steps using stage step_size.
        """
        if self._stage_config:
            step_size = self._stage_config.get("step_size", 0.00002)
        else:
            step_size = 0.00002  # 20nm default
        
        steps = int(abs(distance) / step_size)
        direction = 1 if distance > 0 else -1
        
        return self.jog(direction, steps)


class PiezoController(ABC):
    """
    Abstract base class for piezo voltage controllers (KPZ101, TPZ001).
    
    Piezo controllers output voltage (0-75V or 0-150V) to drive
    piezo actuators. Position is available only with strain gauge feedback.
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        """
        Initialize piezo controller.
        
        Args:
            serial_number: Device serial number
            channel: Channel number (1 for single-channel devices)
        """
        self.serial_number = serial_number
        self.channel = channel
        self.state = ControllerState.DISCONNECTED
        self._voltage_range = (0, 75)  # Default
        self._on_state_change: Optional[Callable[[ControllerState], None]] = None
        self._on_voltage_change: Optional[Callable[[float], None]] = None
    
    @property
    def is_connected(self) -> bool:
        return self.state != ControllerState.DISCONNECTED
    
    @property
    def voltage_min(self) -> float:
        return self._voltage_range[0]
    
    @property
    def voltage_max(self) -> float:
        return self._voltage_range[1]
    
    def configure_stage(self, stage_config: Dict[str, Any]) -> None:
        """Configure for a specific piezo stage."""
        if "voltage_range" in stage_config:
            self._voltage_range = stage_config["voltage_range"]
    
    def set_callbacks(
        self,
        on_state_change: Optional[Callable[[ControllerState], None]] = None,
        on_voltage_change: Optional[Callable[[float], None]] = None
    ) -> None:
        self._on_state_change = on_state_change
        self._on_voltage_change = on_voltage_change
    
    def _set_state(self, new_state: ControllerState) -> None:
        self.state = new_state
        if self._on_state_change:
            self._on_state_change(new_state)
    
    # -------------------------------------------------------------------------
    # Abstract Methods
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the controller."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the controller."""
        pass
    
    @abstractmethod
    def identify(self) -> None:
        """Flash front panel LED."""
        pass
    
    @abstractmethod
    def set_voltage(self, voltage: float) -> bool:
        """
        Set output voltage.
        
        Args:
            voltage: Voltage in range [voltage_min, voltage_max]
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_voltage(self) -> float:
        """
        Get current output voltage.
        
        Returns:
            Current voltage
        """
        pass
    
    @abstractmethod
    def set_position(self, position: float) -> bool:
        """
        Set position (requires strain gauge feedback).
        
        Args:
            position: Position value (0-100% or device units)
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_position(self) -> float:
        """
        Get position (requires strain gauge feedback).
        
        Returns:
            Current position
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get status including voltage, position, mode."""
        pass
    
    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------
    
    def set_voltage_safe(self, voltage: float) -> bool:
        """Set voltage with range checking."""
        voltage = max(self.voltage_min, min(self.voltage_max, voltage))
        return self.set_voltage(voltage)
    
    def zero(self) -> bool:
        """Set voltage to zero."""
        return self.set_voltage(0.0)
    
    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *args):
        self.disconnect()


# ---------------------------------------------------------------------------
# Error Classes
# ---------------------------------------------------------------------------

class MotionControlError(Exception):
    """Base exception for motion control errors."""
    pass


class ConnectionError(MotionControlError):
    """Failed to connect to device."""
    pass


class CommunicationError(MotionControlError):
    """Communication error with device."""
    pass


class MovementError(MotionControlError):
    """Error during movement (limit hit, timeout, etc.)."""
    pass


class ConfigurationError(MotionControlError):
    """Invalid configuration or incompatible stage/controller."""
    pass
