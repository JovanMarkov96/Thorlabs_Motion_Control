"""
APT Motor Adapter - 32-bit COM Fallback

Wraps the existing apt_wrapper.py to implement MotorController interface.
Used when running 32-bit Python without Kinesis .NET support.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import MotorController, ControllerState, ConnectionError, MovementError

# Add path to existing APT wrapper
APT_WRAPPER_PATH = Path(__file__).parent.parent.parent / "Thorlabs_APT" / "src"


class APTMotorAdapter(MotorController):
    """
    APT COM adapter implementing MotorController interface.
    
    Wraps APTMotor from apt_wrapper.py for 32-bit Python fallback.
    Supports KDC101 and TDC001 controllers.
    """
    
    def __init__(self, serial_number: int, channel: int = 1, hw_type: int = 42):
        """
        Initialize APT motor adapter.
        
        Args:
            serial_number: Device serial number
            channel: Channel number (1 for single-channel devices)
            hw_type: APT hardware type code (42=KDC101, 27=TDC001)
        """
        super().__init__(serial_number, channel)
        self._hw_type = hw_type
        self._motor = None
    
    def _get_apt_motor_class(self):
        """Import and return APTMotor class."""
        # Add wrapper path if not already present
        wrapper_str = str(APT_WRAPPER_PATH)
        if wrapper_str not in sys.path:
            sys.path.insert(0, wrapper_str)
        
        from apt_wrapper import APTMotor
        return APTMotor
    
    def connect(self) -> bool:
        """Connect to the APT motor controller."""
        try:
            self._set_state(ControllerState.CONNECTING)
            
            APTMotor = self._get_apt_motor_class()
            
            self._motor = APTMotor(
                serial_number=self.serial_number,
                hw_type=self._hw_type
            )
            self._motor.start()
            
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise ConnectionError(f"Failed to connect to APT motor {self.serial_number}: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from the controller."""
        if self._motor:
            try:
                self._motor.stop_ctrl()
            except Exception:
                pass
            self._motor = None
        
        self._set_state(ControllerState.DISCONNECTED)
    
    def identify(self) -> None:
        """Flash the front panel LED."""
        if self._motor:
            self._motor.identify()
    
    def home(self, wait: bool = True, timeout: float = 60.0) -> bool:
        """Home the stage."""
        if not self._motor:
            return False
        
        try:
            self._set_state(ControllerState.HOMING)
            self._motor.home(wait=wait, timeout=timeout)
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise MovementError(f"Homing failed: {e}")
    
    def move_absolute(
        self, 
        position: float, 
        wait: bool = True, 
        timeout: float = 60.0
    ) -> bool:
        """Move to absolute position."""
        if not self._motor:
            return False
        
        try:
            self._set_state(ControllerState.MOVING)
            self._motor.move_absolute(position, wait=wait, timeout=timeout)
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise MovementError(f"Move failed: {e}")
    
    def move_relative(
        self, 
        distance: float, 
        wait: bool = True, 
        timeout: float = 60.0
    ) -> bool:
        """Move by relative distance."""
        if not self._motor:
            return False
        
        try:
            self._set_state(ControllerState.MOVING)
            self._motor.move_relative(distance, wait=wait, timeout=timeout)
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise MovementError(f"Relative move failed: {e}")
    
    def stop(self) -> None:
        """Stop movement immediately."""
        if self._motor:
            self._motor.stop_move()
            self._set_state(ControllerState.CONNECTED)
    
    def get_position(self) -> float:
        """Get current position."""
        if not self._motor:
            return 0.0
        return self._motor.get_position()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        if not self._motor:
            return {"connected": False}
        
        try:
            bits = self._motor.get_status_bits()
            
            return {
                "connected": True,
                "position": self._motor.get_position(),
                "is_moving": self._motor.is_moving(),
                "is_homed": bool(bits & 0x0400),  # Homed bit
                "status_bits": bits,
            }
        except Exception:
            return {"connected": True}
    
    def is_homed(self) -> bool:
        """Check if device is homed."""
        if not self._motor:
            return False
        
        try:
            bits = self._motor.get_status_bits()
            return bool(bits & 0x0400)
        except Exception:
            return False
