"""
KPZ101 K-Cube Piezo Controller - Kinesis Backend

Uses Thorlabs Kinesis .NET DLLs via pythonnet.
Voltage-controlled piezo driver.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import PiezoController, ControllerState, ConnectionError

# Kinesis DLL path
KINESIS_PATH = Path(r"C:\Program Files\Thorlabs\Kinesis")


class KPZ101Controller(PiezoController):
    """
    KPZ101 K-Cube Piezo Controller.
    
    Voltage-controlled piezo driver (0-75V or 0-150V).
    Position feedback available with strain gauge.
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        super().__init__(serial_number, channel)
        self._device = None
        self._is_initialized = False
    
    def _load_assemblies(self) -> bool:
        """Load required Kinesis .NET assemblies."""
        if self._is_initialized:
            return True
        
        try:
            import clr
            sys.path.append(str(KINESIS_PATH))
            
            clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
            clr.AddReference("Thorlabs.MotionControl.GenericPiezoCLI")
            clr.AddReference("Thorlabs.MotionControl.KCube.PiezoCLI")
            
            self._is_initialized = True
            return True
        
        except Exception as e:
            print(f"Failed to load Kinesis assemblies: {e}")
            return False
    
    def connect(self) -> bool:
        """Connect to the KPZ101 controller."""
        if not self._load_assemblies():
            raise ConnectionError("Failed to load Kinesis assemblies")
        
        try:
            from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
            from Thorlabs.MotionControl.KCube.PiezoCLI import KCubePiezo
            
            self._set_state(ControllerState.CONNECTING)
            
            DeviceManagerCLI.BuildDeviceList()
            
            serial_str = str(self.serial_number)
            self._device = KCubePiezo.CreateKCubePiezo(serial_str)
            
            if self._device is None:
                raise ConnectionError(f"Device {serial_str} not found")
            
            self._device.Connect(serial_str)
            
            if not self._device.IsSettingsInitialized():
                self._device.WaitForSettingsInitialized(5000)
            
            self._device.StartPolling(250)
            time.sleep(0.5)
            
            # Get voltage range from device
            max_voltage = self._device.GetMaxOutputVoltage()
            self._voltage_range = (0, float(max_voltage))
            
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise ConnectionError(f"Failed to connect to KPZ101 {self.serial_number}: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from the controller."""
        if self._device:
            try:
                self._device.StopPolling()
                self._device.Disconnect()
            except Exception:
                pass
            self._device = None
        
        self._set_state(ControllerState.DISCONNECTED)
    
    def identify(self) -> None:
        """Flash the front panel LED."""
        if self._device:
            self._device.IdentifyDevice()
    
    def set_voltage(self, voltage: float) -> bool:
        """
        Set output voltage.
        
        Args:
            voltage: Voltage in range [0, max_voltage]
        """
        if not self._device:
            return False
        
        try:
            from System import Decimal
            
            # Clamp to valid range
            voltage = max(self.voltage_min, min(self.voltage_max, voltage))
            
            self._device.SetOutputVoltage(Decimal(voltage))
            
            if self._on_voltage_change:
                self._on_voltage_change(voltage)
            
            return True
        
        except Exception as e:
            print(f"Failed to set voltage: {e}")
            return False
    
    def get_voltage(self) -> float:
        """Get current output voltage."""
        if not self._device:
            return 0.0
        
        try:
            return float(self._device.GetOutputVoltage())
        except Exception:
            return 0.0
    
    def set_position(self, position: float) -> bool:
        """
        Set position (requires strain gauge feedback).
        
        Args:
            position: Position value (0-32767 device units)
        """
        if not self._device:
            return False
        
        try:
            from System import Decimal
            
            self._device.SetPosition(Decimal(position))
            return True
        
        except Exception as e:
            print(f"Failed to set position: {e}")
            return False
    
    def get_position(self) -> float:
        """Get position (requires strain gauge feedback)."""
        if not self._device:
            return 0.0
        
        try:
            return float(self._device.GetPosition())
        except Exception:
            return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        if not self._device:
            return {"connected": False}
        
        return {
            "connected": True,
            "voltage": self.get_voltage(),
            "position": self.get_position(),
            "voltage_min": self.voltage_min,
            "voltage_max": self.voltage_max,
        }
    
    # -------------------------------------------------------------------------
    # Piezo-specific methods
    # -------------------------------------------------------------------------
    
    def set_zero(self) -> bool:
        """Set current position as zero reference."""
        if not self._device:
            return False
        
        try:
            self._device.SetZero()
            return True
        except Exception as e:
            print(f"Failed to set zero: {e}")
            return False
    
    def get_max_voltage(self) -> float:
        """Get maximum output voltage."""
        if not self._device:
            return 75.0
        
        try:
            return float(self._device.GetMaxOutputVoltage())
        except Exception:
            return 75.0
    
    def set_control_mode(self, mode: str) -> bool:
        """
        Set control mode.
        
        Args:
            mode: "open_loop" (voltage) or "closed_loop" (position)
        """
        if not self._device:
            return False
        
        try:
            from Thorlabs.MotionControl.GenericPiezoCLI import PiezoControlModeTypes
            
            if mode == "open_loop":
                self._device.SetPositionControlMode(PiezoControlModeTypes.OpenLoop)
            elif mode == "closed_loop":
                self._device.SetPositionControlMode(PiezoControlModeTypes.CloseLoop)
            else:
                return False
            
            return True
        
        except Exception as e:
            print(f"Failed to set control mode: {e}")
            return False
    
    def get_control_mode(self) -> str:
        """Get current control mode."""
        if not self._device:
            return "unknown"
        
        try:
            from Thorlabs.MotionControl.GenericPiezoCLI import PiezoControlModeTypes
            
            mode = self._device.GetPositionControlMode()
            
            if mode == PiezoControlModeTypes.OpenLoop:
                return "open_loop"
            elif mode == PiezoControlModeTypes.CloseLoop:
                return "closed_loop"
            else:
                return "unknown"
        
        except Exception:
            return "unknown"
