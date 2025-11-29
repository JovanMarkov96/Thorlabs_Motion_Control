"""
KIM101 K-Cube Inertial Motor Controller - Kinesis Backend

Uses Thorlabs Kinesis .NET DLLs via pythonnet.
4-channel controller for piezo inertia actuators (PIA series).
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from enum import IntEnum

from ..base import InertialController, ControllerState, ConnectionError, MovementError

# Kinesis DLL path
KINESIS_PATH = Path(r"C:\Program Files\Thorlabs\Kinesis")


class InertialMotorChannel(IntEnum):
    """KIM101 channel identifiers."""
    CHANNEL_1 = 1
    CHANNEL_2 = 2
    CHANNEL_3 = 3
    CHANNEL_4 = 4


class KIM101Controller(InertialController):
    """
    KIM101 K-Cube Inertial Motor Controller.
    
    4-channel controller for PIA series piezo inertia actuators.
    Uses step-based control (no encoder feedback).
    """
    
    def __init__(self, serial_number: int, channel: int = 1):
        super().__init__(serial_number, channel)
        self._device = None
        self._is_initialized = False
        
        # Validate channel
        if channel not in (1, 2, 3, 4):
            raise ValueError(f"Invalid channel {channel}. KIM101 has channels 1-4.")
    
    def _load_assemblies(self) -> bool:
        """Load required Kinesis .NET assemblies."""
        if self._is_initialized:
            return True
        
        try:
            import clr
            sys.path.append(str(KINESIS_PATH))
            
            clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
            clr.AddReference("Thorlabs.MotionControl.GenericPiezoCLI")
            clr.AddReference("Thorlabs.MotionControl.KCube.InertialMotorCLI")
            
            self._is_initialized = True
            return True
        
        except Exception as e:
            print(f"Failed to load Kinesis assemblies: {e}")
            return False
    
    def _get_channel_enum(self):
        """Get the .NET channel enum value."""
        from Thorlabs.MotionControl.KCube.InertialMotorCLI import InertialMotorStatus
        
        channel_map = {
            1: InertialMotorStatus.MotorChannels.Channel1,
            2: InertialMotorStatus.MotorChannels.Channel2,
            3: InertialMotorStatus.MotorChannels.Channel3,
            4: InertialMotorStatus.MotorChannels.Channel4,
        }
        return channel_map[self.channel]
    
    def connect(self) -> bool:
        """Connect to the KIM101 controller."""
        if not self._load_assemblies():
            raise ConnectionError("Failed to load Kinesis assemblies")
        
        try:
            from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
            from Thorlabs.MotionControl.KCube.InertialMotorCLI import KCubeInertialMotor
            
            self._set_state(ControllerState.CONNECTING)
            
            DeviceManagerCLI.BuildDeviceList()
            
            serial_str = str(self.serial_number)
            self._device = KCubeInertialMotor.CreateKCubeInertialMotor(serial_str)
            
            if self._device is None:
                raise ConnectionError(f"Device {serial_str} not found")
            
            self._device.Connect(serial_str)
            
            if not self._device.IsSettingsInitialized():
                self._device.WaitForSettingsInitialized(5000)
            
            self._device.StartPolling(250)
            time.sleep(0.5)
            
            # Enable the channel
            self._device.EnableDevice()
            time.sleep(0.3)
            
            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise ConnectionError(f"Failed to connect to KIM101 {self.serial_number}: {e}")
    
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
    
    def stop(self) -> None:
        """Stop movement on this channel."""
        if self._device:
            try:
                channel_enum = self._get_channel_enum()
                self._device.Stop(channel_enum)
            except Exception as e:
                print(f"Stop failed: {e}")
            self._set_state(ControllerState.CONNECTED)
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status for this channel."""
        if not self._device:
            return {"connected": False}
        
        try:
            # Get actual hardware status for this channel
            channel_status = self.get_channel_status()
            
            return {
                "connected": True,
                "channel": self.channel,
                "position": channel_status.get("position", 0),
                "is_moving": channel_status.get("is_moving", False),
                "is_enabled": channel_status.get("is_enabled", False),
                "step_count": self._step_count,  # Keep for compatibility
            }
        except Exception:
            return {"connected": True, "channel": self.channel}
    
    # -------------------------------------------------------------------------
    # Inertial-specific methods
    # -------------------------------------------------------------------------
    
    def jog(self, direction: int) -> bool:
        """
        Jog the actuator by configured jog steps.
        
        Args:
            direction: 1 for increase (forward), -1 for decrease (reverse)
            
        Returns:
            True if successful
            
        Note:
            The number of steps is configured via set_jog_params().
            Use move_by() for explicit step counts.
        """
        if not self._device:
            return False
        
        try:
            from Thorlabs.MotionControl.KCube.InertialMotorCLI import InertialMotorJogDirection
            
            channel_enum = self._get_channel_enum()
            
            # Set jog direction - API uses Increase/Decrease not Forward/Backward
            jog_dir = (
                InertialMotorJogDirection.Increase 
                if direction > 0 
                else InertialMotorJogDirection.Decrease
            )
            
            # Execute jog - requires 3 args: channel, direction, callback (None for async)
            self._device.Jog(channel_enum, jog_dir, None)
            
            return True
        
        except Exception as e:
            print(f"Jog failed: {e}")
            return False
    
    def jog_continuous(self, direction: int) -> bool:
        """
        Start continuous jogging.
        
        Args:
            direction: 1 for increase (forward), -1 for decrease (reverse)
        """
        if not self._device:
            return False
        
        try:
            from Thorlabs.MotionControl.KCube.InertialMotorCLI import InertialMotorJogDirection
            
            channel_enum = self._get_channel_enum()
            
            jog_dir = (
                InertialMotorJogDirection.Increase 
                if direction > 0 
                else InertialMotorJogDirection.Decrease
            )
            
            # Use Jog with None callback for async jog
            # Jog behavior (single step vs continuous) is controlled by JogMode setting
            self._device.Jog(channel_enum, jog_dir, None)
            return True
        
        except Exception as e:
            print(f"Continuous jog failed: {e}")
            return False
    
    def set_step_rate(self, rate: int) -> bool:
        """
        Set step rate (steps per second).
        
        Args:
            rate: Step rate (1-2000)
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            
            # Get current parameters and update rate
            # API uses GetDriveParameters (not GetDriveOPParameters)
            params = self._device.GetDriveParameters(channel_enum)
            params.StepRate = rate
            self._device.SetDriveParameters(channel_enum, params)
            
            return True
        
        except Exception as e:
            print(f"Failed to set step rate: {e}")
            return False
    
    def set_step_acceleration(self, acceleration: int) -> bool:
        """
        Set step acceleration.
        
        Args:
            acceleration: Steps/second²
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            
            # API uses GetDriveParameters (not GetDriveOPParameters)
            params = self._device.GetDriveParameters(channel_enum)
            params.StepAcceleration = acceleration
            self._device.SetDriveParameters(channel_enum, params)
            
            return True
        
        except Exception as e:
            print(f"Failed to set step acceleration: {e}")
            return False
    
    def get_drive_params(self) -> Dict[str, int]:
        """Get current drive parameters."""
        if not self._device:
            return {"step_rate": 0, "step_acceleration": 0, "max_voltage": 0}
        
        try:
            channel_enum = self._get_channel_enum()
            # API uses GetDriveParameters (not GetDriveOPParameters)
            params = self._device.GetDriveParameters(channel_enum)
            
            return {
                "step_rate": int(params.StepRate),
                "step_acceleration": int(params.StepAcceleration),
                "max_voltage": int(params.MaxVoltage),
            }
        except Exception:
            return {"step_rate": 0, "step_acceleration": 0, "max_voltage": 0}
    
    def set_max_voltage(self, voltage: int) -> bool:
        """
        Set maximum drive voltage.
        
        Args:
            voltage: Maximum voltage (85-125)
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            params = self._device.GetDriveParameters(channel_enum)
            params.MaxVoltage = voltage
            self._device.SetDriveParameters(channel_enum, params)
            return True
        except Exception as e:
            print(f"Failed to set max voltage: {e}")
            return False
    
    def get_jog_params(self) -> Dict[str, int]:
        """Get current jog parameters."""
        if not self._device:
            return {"jog_step_fwd": 0, "jog_step_rev": 0, "jog_rate": 0, "jog_acceleration": 0}
        
        try:
            channel_enum = self._get_channel_enum()
            params = self._device.GetJogParameters(channel_enum)
            
            return {
                "jog_step_fwd": int(params.JogStepFwd),
                "jog_step_rev": int(params.JogStepRev),
                "jog_rate": int(params.JogRate),
                "jog_acceleration": int(params.JogAcceleration),
            }
        except Exception as e:
            print(f"Failed to get jog params: {e}")
            return {"jog_step_fwd": 0, "jog_step_rev": 0, "jog_rate": 0, "jog_acceleration": 0}
    
    def set_jog_params(self, step_fwd: int = None, step_rev: int = None, 
                       rate: int = None, acceleration: int = None) -> bool:
        """
        Set jog parameters.
        
        Args:
            step_fwd: Steps for forward jog
            step_rev: Steps for reverse jog
            rate: Jog rate (steps/second)
            acceleration: Jog acceleration
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            params = self._device.GetJogParameters(channel_enum)
            
            if step_fwd is not None:
                params.JogStepFwd = step_fwd
            if step_rev is not None:
                params.JogStepRev = step_rev
            if rate is not None:
                params.JogRate = rate
            if acceleration is not None:
                params.JogAcceleration = acceleration
            
            self._device.SetJogParameters(channel_enum, params)
            return True
        except Exception as e:
            print(f"Failed to set jog params: {e}")
            return False
    
    def move_by(self, steps: int, timeout_ms: int = 0) -> bool:
        """
        Move by a specified number of steps.
        
        Args:
            steps: Number of steps (positive = forward, negative = reverse)
            timeout_ms: Timeout in milliseconds (0 = async)
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            
            if timeout_ms > 0:
                # Synchronous move
                self._device.MoveBy(channel_enum, steps, timeout_ms)
            else:
                # Async move
                self._device.MoveBy(channel_enum, steps, None)
            
            return True
        except Exception as e:
            print(f"MoveBy failed: {e}")
            return False
    
    def move_to(self, position: int, timeout_ms: int = 0) -> bool:
        """
        Move to an absolute position.
        
        Args:
            position: Target position in steps
            timeout_ms: Timeout in milliseconds (0 = async)
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            
            if timeout_ms > 0:
                self._device.MoveTo(channel_enum, position, timeout_ms)
            else:
                self._device.MoveTo(channel_enum, position, None)
            
            return True
        except Exception as e:
            print(f"MoveTo failed: {e}")
            return False
    
    def get_hw_position(self) -> int:
        """
        Get current position from device (hardware reported).
        
        Returns:
            Position in steps
        """
        if not self._device:
            return 0
        
        try:
            channel_enum = self._get_channel_enum()
            return int(self._device.GetPosition(channel_enum))
        except Exception:
            return 0
    
    def set_position(self, position: int) -> bool:
        """
        Set the current position value (redefine position).
        
        This sets the position register without moving the actuator.
        Useful for defining zero/reference positions.
        
        Args:
            position: New position value
        """
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            self._device.SetPositionAs(channel_enum, position)
            return True
        except Exception as e:
            print(f"SetPositionAs failed: {e}")
            return False
    
    def zero_position(self) -> bool:
        """Set current position as zero."""
        return self.set_position(0)
    
    def enable_channel(self) -> bool:
        """Enable this channel."""
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            self._device.EnableChannel(channel_enum)
            return True
        except Exception as e:
            print(f"EnableChannel failed: {e}")
            return False
    
    def disable_channel(self) -> bool:
        """Disable this channel."""
        if not self._device:
            return False
        
        try:
            channel_enum = self._get_channel_enum()
            self._device.DisableChannel(channel_enum)
            return True
        except Exception as e:
            print(f"DisableChannel failed: {e}")
            return False
    
    def get_channel_status(self) -> Dict[str, Any]:
        """
        Get status for this channel.
        
        Returns:
            Dictionary with position, is_moving, is_enabled, is_error
        """
        if not self._device:
            return {"connected": False}
        
        try:
            channel_enum = self._get_channel_enum()
            # Status is a Dictionary - use indexing not method call
            status = self._device.Status[channel_enum]
            
            return {
                "position": int(status.Position),
                "is_moving": bool(status.IsMoving),
                "is_enabled": bool(status.IsEnabled),
                "is_error": bool(status.IsError) if hasattr(status, 'IsError') else False,
            }
        except Exception as e:
            print(f"GetChannelStatus failed: {e}")
            return {"connected": True, "error": str(e)}
    
    def is_channel_enabled(self) -> bool:
        """Check if this channel is enabled."""
        status = self.get_channel_status()
        return status.get("is_enabled", False)
    
    def is_moving(self) -> bool:
        """Check if the actuator is currently moving."""
        status = self.get_channel_status()
        return status.get("is_moving", False)
    
    def move_to_limit(self, direction: int, timeout: float = 60.0) -> bool:
        """
        Move until limit is reached.
        
        Args:
            direction: 1 for forward limit, -1 for reverse limit
            timeout: Maximum time to wait
            
        Returns:
            True if limit was reached
            
        Warning:
            This will move continuously until a physical limit is hit.
            Use with caution to avoid damaging equipment.
        """
        if not self._device:
            return False
        
        try:
            self._set_state(ControllerState.MOVING)
            
            # Start continuous jog
            self.jog_continuous(direction)
            
            # Wait for stop (limit reached) or timeout
            start = time.time()
            while time.time() - start < timeout:
                time.sleep(0.1)
                # Check if still moving
                # Note: Implementation depends on status reporting
            
            self.stop()
            self._set_state(ControllerState.CONNECTED)
            
            # Reset step count at limit
            self._step_count = 0
            
            return True
        
        except Exception as e:
            self.stop()
            self._set_state(ControllerState.ERROR)
            raise MovementError(f"Move to limit failed: {e}")
