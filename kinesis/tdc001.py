"""
TDC001 T-Cube DC Servo Controller - Kinesis Backend

Uses Thorlabs Kinesis .NET DLLs via pythonnet.
Legacy controller, similar to KDC101 but T-Cube form factor.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..base import MotorController, ControllerState, ConnectionError, MovementError

# Kinesis DLL path
KINESIS_PATH = Path(r"C:\Program Files\Thorlabs\Kinesis")

# ---------------------------------------------------------------------------
# SLOW BY DEFAULT.  Every TDC001 in Lab185 turns a 1064 nm waveplate, and those
# angles ARE the calibration: the co-prop gate sits on a latitude that has to be
# held to |eps| ~ 0.02, which is a fraction of a degree on the dial.  Kinesis
# hands a PRM1-Z8 a default max velocity around 25 deg/s, and slamming a
# worm-gear rotation mount at that speed lands it on the wrong side of its own
# backlash -- the mount reads the right angle and the polarization is somewhere
# else.  That is a lost gate setting, and re-finding it costs a night.
#
# 2 deg/s with matched acceleration is ~12x slower than the Kinesis default.  A
# typical campaign step (a few degrees) still completes in a second or two; the
# worst case, a full 360 deg, takes 180 s, which is why the move timeout below
# is generous rather than the old 60 s.  Do not raise these to "save time" --
# the time they save is measured in seconds and the time they cost is measured
# in nights.  Override per-instance only for a deliberate fast bulk move.
DEFAULT_MAX_VELOCITY_DEG_S = 2.0
DEFAULT_ACCELERATION_DEG_S2 = 2.0
# A slow stage needs a long leash: 360 deg at 2 deg/s is 180 s.  The timeout is
# a stuck-stage guard, not a speed budget.
DEFAULT_MOVE_TIMEOUT_S = 300.0


class TDC001Controller(MotorController):
    """
    TDC001 T-Cube DC Servo Motor Controller (Legacy).

    Supports the same stages as KDC101 (PRM1Z8, Z825B, MTS25/50, etc.)
    but in the older T-Cube form factor.

    Connects SLOW: `connect()` applies DEFAULT_MAX_VELOCITY_DEG_S /
    DEFAULT_ACCELERATION_DEG_S2 unless the caller overrides them, so every
    consumer (the waveplate GUI, ServerLab, the campaign scripts) inherits the
    same gentle motion without having to remember to ask for it.
    """

    def __init__(self, serial_number: int, channel: int = 1,
                 max_velocity: Optional[float] = None,
                 acceleration: Optional[float] = None):
        super().__init__(serial_number, channel)
        self._device = None
        self._is_initialized = False
        self.max_velocity = (DEFAULT_MAX_VELOCITY_DEG_S if max_velocity is None
                             else float(max_velocity))
        self.acceleration = (DEFAULT_ACCELERATION_DEG_S2 if acceleration is None
                             else float(acceleration))
    
    def _load_assemblies(self) -> bool:
        """Load required Kinesis .NET assemblies."""
        if self._is_initialized:
            return True
        
        try:
            import clr
            sys.path.append(str(KINESIS_PATH))
            
            clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
            clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
            clr.AddReference("Thorlabs.MotionControl.TCube.DCServoCLI")
            
            self._is_initialized = True
            return True
        
        except Exception as e:
            print(f"Failed to load Kinesis assemblies: {e}")
            return False
    
    def connect(self, enable: bool = True) -> bool:
        """
        Connect to the TDC001 controller.

        Args:
            enable: Energize the servo drive as part of connecting. True is
                the default and matches the previous behaviour. Pass False
                for a read-only monitoring connection: status polling,
                position reads and LoadMotorConfiguration still happen, but
                the drive stays disabled, so no command can move the stage
                until enable() is called explicitly.
        """
        if not self._load_assemblies():
            raise ConnectionError("Failed to load Kinesis assemblies")
        
        try:
            from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
            from Thorlabs.MotionControl.TCube.DCServoCLI import TCubeDCServo
            
            self._set_state(ControllerState.CONNECTING)
            
            DeviceManagerCLI.BuildDeviceList()
            
            serial_str = str(self.serial_number)
            self._device = TCubeDCServo.CreateTCubeDCServo(serial_str)
            
            if self._device is None:
                raise ConnectionError(f"Device {serial_str} not found")
            
            self._device.Connect(serial_str)
            
            if not self._device.IsSettingsInitialized():
                self._device.WaitForSettingsInitialized(5000)
            
            self._device.StartPolling(250)
            time.sleep(0.5)

            if enable:
                self._device.EnableDevice()
                time.sleep(0.5)

            motor_config = self._device.LoadMotorConfiguration(serial_str)

            # Apply the slow defaults AFTER LoadMotorConfiguration -- that call
            # installs the stage profile (and with it Thorlabs' fast default
            # velocity), so setting them earlier would be overwritten.  Guarded:
            # a controller that refuses SetVelocityParams must still connect,
            # but it must SAY so rather than silently running fast.
            self.apply_motion_limits()

            self._set_state(ControllerState.CONNECTED)
            return True
        
        except Exception as e:
            self._set_state(ControllerState.ERROR)
            raise ConnectionError(f"Failed to connect to TDC001 {self.serial_number}: {e}")
    
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

    def enable(self) -> None:
        """
        Energize the servo drive. Required before any move if the device was
        connected with enable=False. Safe to call when already enabled.
        """
        if self._device:
            self._device.EnableDevice()
            time.sleep(0.5)
    
    def home(self, wait: bool = True, timeout: float = 60.0) -> bool:
        """Home the stage."""
        if not self._device:
            return False
        
        try:
            self._set_state(ControllerState.HOMING)
            
            self._device.Home(int(timeout * 1000) if wait else 0)
            
            if wait:
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
        timeout: float = DEFAULT_MOVE_TIMEOUT_S
    ) -> bool:
        """Move to absolute position.

        NB the timeout default is generous (see DEFAULT_MOVE_TIMEOUT_S): the
        stage is deliberately slow, so 60 s -- the old default -- would abort a
        legitimate move of more than ~120 deg partway through, leaving the plate
        at an angle nobody recorded.
        """
        if not self._device:
            return False
        
        try:
            self._set_state(ControllerState.MOVING)
            
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
        timeout: float = DEFAULT_MOVE_TIMEOUT_S
    ) -> bool:
        """Move by relative distance.  Same generous timeout as move_absolute."""
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
            self._device.Stop(0)
            self._set_state(ControllerState.CONNECTED)
    
    def get_position(self) -> float:
        """Get current position."""
        if not self._device:
            return 0.0
        # .NET Decimal needs conversion via Decimal.ToDouble
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
    
    def apply_motion_limits(self) -> bool:
        """Push self.max_velocity / self.acceleration to the cube.

        Called by connect().  Separate so it can be re-applied after anything
        that reloads the stage profile, and so the GUI can report what actually
        took effect.  Returns True only if BOTH landed; prints loudly otherwise,
        because the failure mode is a stage that silently keeps Thorlabs' fast
        default and quietly loses the waveplate calibration to backlash.
        """
        if not self._device:
            return False
        ok_v = self.set_velocity(self.max_velocity)
        ok_a = self.set_acceleration(self.acceleration)
        if not (ok_v and ok_a):
            print(f"[TDC001 {self.serial_number}]: WARNING -- could not apply slow "
                  f"motion limits (velocity ok={ok_v}, acceleration ok={ok_a}). "
                  f"The stage may move at the Kinesis default speed; waveplate "
                  f"angles set now are NOT backlash-trustworthy.")
            return False
        got = self.get_velocity_params()
        print(f"[TDC001 {self.serial_number}]: motion limited to "
              f"{got.get('max_velocity', float('nan')):.3g} deg/s, "
              f"accel {got.get('acceleration', float('nan')):.3g} deg/s^2")
        return True

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
