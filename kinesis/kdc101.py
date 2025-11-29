"""
KDC101 K-Cube DC Servo Controller - Kinesis Backend

Uses Thorlabs Kinesis .NET DLLs via pythonnet.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import MotorController, ControllerState, ConnectionError, MovementError

# Kinesis DLL path
KINESIS_PATH = Path(r"C:\Program Files\Thorlabs\Kinesis")


class KDC101Controller(MotorController):
    """
    KDC101 K-Cube DC Servo Motor Controller.
    
    Supports stages like PRM1Z8 (rotation), Z825B (linear), MTS25/50, etc.
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
            clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
            clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
            
            self._is_initialized = True
            return True
        
        except Exception as e:
            print(f"Failed to load Kinesis assemblies: {e}")
            return False
    
    def connect(self) -> bool:
        """Connect to the KDC101 controller."""
        if not self._load_assemblies():
            raise ConnectionError("Failed to load Kinesis assemblies")
        
        try:
            from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
            from Thorlabs.MotionControl.KCube.DCServoCLI import KCubeDCServo
            
            self._set_state(ControllerState.CONNECTING)
            
            # Build device list
            DeviceManagerCLI.BuildDeviceList()
            
            # Create device instance
            serial_str = str(self.serial_number)
            self._device = KCubeDCServo.CreateKCubeDCServo(serial_str)
            
            if self._device is None:
                raise ConnectionError(f"Device {serial_str} not found")
            
            # Connect
            self._device.Connect(serial_str)
            
            # Wait for settings to initialize
            if not self._device.IsSettingsInitialized():
                self._device.WaitForSettingsInitialized(5000)
            
            # Start polling for status updates
            self._device.StartPolling(250)
            time.sleep(0.5)
            
            # Enable device
            self._device.EnableDevice()
            time.sleep(0.5)
            
            # Load motor configuration
            motor_config = self._device.LoadMotorConfiguration(serial_str)
            
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise ConnectionError(f"Failed to connect to KDC101 {self.serial_number}: {e}")
    
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
    
    def home(self, wait: bool = True, timeout: float = 60.0) -> bool:
        """
        Home the stage.
        
        Args:
            wait: If True, block until homing completes
            timeout: Maximum wait time in seconds
        """
        if not self._device:
            return False
        
        try:
            self._set_state(ControllerState.HOMING)
            
            # Start homing
            self._device.Home(int(timeout * 1000) if wait else 0)
            
            if wait:
                # Wait for completion
                start = time.time()
                while self._device.Status.IsHoming:
                    if time.time() - start > timeout:
                        raise MovementError("Homing timeout")
                    time.sleep(0.1)
            
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
        if not self._device:
            return False
        
        try:
            self._set_state(ControllerState.MOVING)
            
            # Convert to Decimal for .NET
            from System import Decimal
            pos_decimal = Decimal(position)
            
            self._device.MoveTo(pos_decimal, int(timeout * 1000) if wait else 0)
            
            if wait:
                start = time.time()
                while self._device.Status.IsMoving:
                    if time.time() - start > timeout:
                        raise MovementError("Move timeout")
                    time.sleep(0.1)
            
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
        if not self._device:
            return False
        
        try:
            self._set_state(ControllerState.MOVING)
            
            from Thorlabs.MotionControl.GenericMotorCLI import MotorDirection
            
            direction = MotorDirection.Forward if distance > 0 else MotorDirection.Backward
            
            from System import Decimal
            dist_decimal = Decimal(abs(distance))
            
            self._device.MoveRelative(direction, dist_decimal, int(timeout * 1000) if wait else 0)
            
            if wait:
                start = time.time()
                while self._device.Status.IsMoving:
                    if time.time() - start > timeout:
                        raise MovementError("Move timeout")
                    time.sleep(0.1)
            
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise MovementError(f"Relative move failed: {e}")
    
    def stop(self) -> None:
        """Stop movement immediately."""
        if self._device:
            self._device.Stop(0)  # Immediate stop
            self._set_state(ControllerState.CONNECTED)
    
    def get_position(self) -> float:
        """Get current position in device units."""
        if not self._device:
            return 0.0
        
        # .NET Decimal needs conversion via str or Decimal.ToDouble
        pos = self._device.Position
        from System import Decimal as NetDecimal
        return float(NetDecimal.ToDouble(pos))
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status."""
        if not self._device:
            return {"connected": False}
        
        status = self._device.Status
        from System import Decimal as NetDecimal
        
        # Helper to safely convert .NET types to Python float
        def to_float(value):
            try:
                if hasattr(value, 'GetType') and 'Decimal' in str(value.GetType()):
                    return float(NetDecimal.ToDouble(value))
                return float(value)
            except Exception:
                return 0.0
        
        position = to_float(self._device.Position)
        velocity = to_float(status.Velocity) if hasattr(status, 'Velocity') else 0.0
        
        return {
            "connected": True,
            "position": position,
            "velocity": velocity,
            "is_moving": status.IsMoving,
            "is_homing": status.IsHoming,
            "is_homed": status.IsHomed,
            "forward_limit": status.IsForwardHardwareLimitActive if hasattr(status, 'IsForwardHardwareLimitActive') else False,
            "reverse_limit": status.IsReverseHardwareLimitActive if hasattr(status, 'IsReverseHardwareLimitActive') else False,
            "enabled": self._device.IsEnabled if hasattr(self._device, 'IsEnabled') else True,
        }
    
    def set_velocity(self, velocity: float) -> bool:
        """Set maximum velocity."""
        if not self._device:
            return False
        
        try:
            vel_params = self._device.GetVelocityParams()
            from System import Decimal
            vel_params.MaxVelocity = Decimal(velocity)
            self._device.SetVelocityParams(vel_params)
            return True
        except Exception as e:
            print(f"Failed to set velocity: {e}")
            return False
    
    def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration."""
        if not self._device:
            return False
        
        try:
            vel_params = self._device.GetVelocityParams()
            from System import Decimal
            vel_params.Acceleration = Decimal(acceleration)
            self._device.SetVelocityParams(vel_params)
            return True
        except Exception as e:
            print(f"Failed to set acceleration: {e}")
            return False
    
    def get_velocity_params(self) -> Dict[str, float]:
        """Get velocity parameters."""
        if not self._device:
            return {"max_velocity": 0, "acceleration": 0}
        
        try:
            vel_params = self._device.GetVelocityParams()
            return {
                "max_velocity": float(vel_params.MaxVelocity),
                "acceleration": float(vel_params.Acceleration),
            }
        except Exception:
            return {"max_velocity": 0, "acceleration": 0}
    
    def is_homed(self) -> bool:
        """Check if device is homed."""
        if not self._device:
            return False
        return self._device.Status.IsHomed
    
    def get_stage_info(self) -> Optional[Dict[str, Any]]:
        """
        Get connected stage information from motor EEPROM.
        
        Returns:
            Dict with stage info or None:
                - part_number: Stage model (e.g., "PRM1Z8")
                - serial_number: Stage serial number
                - stage_id: Internal stage ID
        """
        if not self._device:
            return None
        
        try:
            stage_def = self._device.GetStageDefinition()
            
            if stage_def and stage_def.PartNumber:
                return {
                    "part_number": str(stage_def.PartNumber).strip(),
                    "serial_number": str(stage_def.SerialNumber).strip() if stage_def.SerialNumber else None,
                    "stage_id": int(stage_def.StageID) if stage_def.StageID else None,
                }
            return None
        except Exception as e:
            print(f"Failed to get stage info: {e}")
            return None
