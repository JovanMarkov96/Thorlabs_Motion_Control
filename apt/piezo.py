"""
APT Piezo Adapter - 32-bit COM Fallback

Wraps the existing apt_wrapper.py to implement PiezoController interface.
Used when running 32-bit Python without Kinesis .NET support.
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import PiezoController, ControllerState, ConnectionError

# Add path to existing APT wrapper
APT_WRAPPER_PATH = Path(__file__).parent.parent.parent / "Thorlabs_APT" / "src"


class APTPiezoAdapter(PiezoController):
    """
    APT COM adapter implementing PiezoController interface.
    
    Wraps APTPiezo from apt_wrapper.py for 32-bit Python fallback.
    Supports KPZ101 and TPZ001 controllers.
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        """
        Initialize APT piezo adapter.
        
        Args:
            serial_number: Device serial number
            channel: Channel number (1 for single-channel devices)
        """
        super().__init__(serial_number, channel)
        self._piezo = None
    
    def _get_apt_piezo_class(self):
        """Import and return APTPiezo class."""
        # Add wrapper path if not already present
        wrapper_str = str(APT_WRAPPER_PATH)
        if wrapper_str not in sys.path:
            sys.path.insert(0, wrapper_str)
        
        from apt_wrapper import APTPiezo
        return APTPiezo
    
    def connect(self) -> bool:
        """Connect to the APT piezo controller."""
        try:
            self._set_state(ControllerState.CONNECTING)
            
            APTPiezo = self._get_apt_piezo_class()
            
            self._piezo = APTPiezo(serial_number=self.serial_number)
            self._piezo.start()
            
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise ConnectionError(f"Failed to connect to APT piezo {self.serial_number}: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from the controller."""
        if self._piezo:
            try:
                self._piezo.stop_ctrl()
            except Exception:
                pass
            self._piezo = None
        
        self._set_state(ControllerState.DISCONNECTED)
    
    def identify(self) -> None:
        """Flash the front panel LED."""
        if self._piezo:
            self._piezo.identify()
    
    def set_voltage(self, voltage: float) -> bool:
        """Set output voltage."""
        if not self._piezo:
            return False
        
        try:
            # Clamp to valid range
            voltage = max(self.voltage_min, min(self.voltage_max, voltage))
            
            self._piezo.set_voltage(voltage)
            
            if self._on_voltage_change:
                self._on_voltage_change(voltage)
            
            return True
        
        except Exception as e:
            print(f"Failed to set voltage: {e}")
            return False
    
    def get_voltage(self) -> float:
        """Get current output voltage."""
        if not self._piezo:
            return 0.0
        
        try:
            return self._piezo.get_voltage()
        except Exception:
            return 0.0
    
    def set_position(self, position: float) -> bool:
        """Set position (requires strain gauge feedback)."""
        if not self._piezo:
            return False
        
        try:
            self._piezo.set_position(position)
            return True
        except Exception as e:
            print(f"Failed to set position: {e}")
            return False
    
    def get_position(self) -> float:
        """Get position (requires strain gauge feedback)."""
        if not self._piezo:
            return 0.0
        
        try:
            return self._piezo.get_position()
        except Exception:
            return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        if not self._piezo:
            return {"connected": False}
        
        return {
            "connected": True,
            "voltage": self.get_voltage(),
            "position": self.get_position(),
            "voltage_min": self.voltage_min,
            "voltage_max": self.voltage_max,
        }
