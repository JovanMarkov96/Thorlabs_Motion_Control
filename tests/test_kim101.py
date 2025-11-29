"""
KIM101 K-Cube Inertial Motor Controller - Comprehensive Test Suite
===================================================================

This module provides a comprehensive test suite for the Thorlabs KIM101
K-Cube Inertial Motor Controller, validating all API functionality via
direct Kinesis .NET DLL calls.

Controller Specifications
-------------------------
- **Model:** KIM101
- **Type:** Piezo Inertia Actuator Driver
- **Channels:** 4 (independent)
- **Serial Prefix:** 97
- **Interface:** USB (Kinesis)
- **Step Resolution:** ~20nm typical

Compatible Actuators
--------------------
- PIA13 — 13mm Piezo Inertia Actuator
- PIA25 — 25mm Piezo Inertia Actuator
- PIA50 — 50mm Piezo Inertia Actuator
- PIAK10 — 10mm Compact Piezo Inertia Actuator
- PIAK25 — 25mm Compact Piezo Inertia Actuator

Test Coverage (27 Tests)
------------------------
1. Device Discovery
2. Connection Management
3. Device Information & Identification
4. All 4 Channel Status Queries
5. Drive Parameter Get/Set
6. Jog Parameter Get/Set
7. Channel Enable/Disable
8. Position Reading & Zeroing
9. Jog Operations (Forward/Reverse)
10. Relative Movement (MoveBy)
11. Absolute Movement (MoveTo)
12. Stop Command
13. Multi-Channel Operations

Usage
-----
Command line::

    python test_kim101.py

Programmatic::

    from test_kim101 import KIM101TestSuite
    suite = KIM101TestSuite(serial_number=97101306)
    success = suite.run_all_tests()

Requirements
------------
- KIM101 controller connected via USB
- Thorlabs Kinesis v1.14+ installed
- Python 3.8+ with pythonnet

API Notes
---------
- Status is accessed via ``device.Status[channel]`` (Dictionary, not method)
- Jog requires 3 arguments: ``Jog(channel, direction, callback)``
- Direction enum: ``InertialMotorJogDirection.Increase/Decrease``
- Drive params via: ``GetDriveParameters()``, ``SetDriveParameters()``

See Also
--------
- tests/README.md for full testing documentation
"""
import sys
import time
import os

# Setup paths BEFORE importing clr
KINESIS_PATH = r"C:\Program Files\Thorlabs\Kinesis"
if KINESIS_PATH not in sys.path:
    sys.path.insert(0, KINESIS_PATH)

# Add workspace root
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Now import CLR and .NET assemblies
import clr
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.InertialMotorCLI")

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.KCube.InertialMotorCLI import (
    KCubeInertialMotor,
    InertialMotorStatus,
    InertialMotorJogDirection,
)


class KIM101TestSuite:
    """
    Comprehensive test suite for KIM101 K-Cube Inertial Motor Controller.
    
    This test suite validates all functionality of the KIM101 4-channel
    inertial motor controller including device discovery, connection
    management, drive/jog parameter configuration, and motion control
    across all channels.
    
    Attributes:
        device: Raw Kinesis KCubeInertialMotor .NET object.
        serial: Device serial number (string, auto-discovered or pre-set).
        channel: Current test channel (InertialMotorStatus.MotorChannels).
        results: List of (test_name, passed, details) tuples.
        passed: Count of passed tests.
        failed: Count of failed tests.
    
    Example:
        >>> suite = KIM101TestSuite(serial_number=97101306)
        >>> success = suite.run_all_tests()
        >>> print(f"All 4 channels tested: {suite.passed} passed")
    
    Note:
        This test suite uses direct Kinesis DLL access rather than the
        ThorlabsMotionControl wrapper for comprehensive API validation.
    """
    
    def __init__(self, serial_number: int = None):
        self.device = None
        self.serial = str(serial_number) if serial_number else None  # Can be pre-set or discovered
        self.channel = None
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def log(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "PASS" if passed else "FAIL"
        self.results.append((test_name, passed, details))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  [{status}] {test_name}")
        if details:
            for line in details.split('\n'):
                print(f"         {line}")
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 70)
        print("KIM101 COMPREHENSIVE TEST SUITE")
        print("K-Cube Inertial Motor Controller (4-Channel)")
        print("=" * 70)
        
        try:
            # Setup
            if not self.test_discovery():
                print("\n[ABORT] No KIM101 device found!")
                return False
            
            if not self.test_connect():
                print("\n[ABORT] Failed to connect!")
                return False
            
            # Run all tests
            self.test_device_info()
            self.test_identify()
            self.test_all_channels_status()
            self.test_drive_parameters()
            self.test_set_drive_parameters()
            self.test_jog_parameters()
            self.test_set_jog_parameters()
            self.test_enable_disable_channel()
            self.test_get_position()
            self.test_set_position_as_zero()
            self.test_jog_forward()
            self.test_jog_reverse()
            self.test_move_by_positive()
            self.test_move_by_negative()
            self.test_move_to()
            self.test_stop()
            self.test_is_moving()
            self.test_multi_channel()
            
        finally:
            self.test_disconnect()
        
        # Summary
        self.print_summary()
        return self.failed == 0
    
    # =========================================================================
    # DISCOVERY & CONNECTION
    # =========================================================================
    
    def test_discovery(self) -> bool:
        """Test 1: Device Discovery"""
        print("\n" + "-" * 70)
        print("TEST: Device Discovery")
        print("-" * 70)
        
        try:
            DeviceManagerCLI.BuildDeviceList()
            devices = list(DeviceManagerCLI.GetDeviceList())
            kim_serials = [s for s in devices if s.startswith('97')]
            
            # If serial was pre-set, verify it exists
            if self.serial:
                if self.serial in kim_serials:
                    self.log("Discovery (pre-set)", True, f"Found KIM101: {self.serial}")
                    return True
                else:
                    self.log("Discovery (pre-set)", False, f"Device {self.serial} not found")
                    return False
            
            if kim_serials:
                self.serial = kim_serials[0]
                self.log("Discovery", True, f"Found KIM101: {self.serial}")
                return True
            else:
                self.log("Discovery", False, "No KIM101 found (serial starts with 97)")
                return False
        except Exception as e:
            self.log("Discovery", False, str(e))
            return False
    
    def test_connect(self) -> bool:
        """Test 2: Connect to Device"""
        print("\n" + "-" * 70)
        print("TEST: Connection")
        print("-" * 70)
        
        try:
            self.device = KCubeInertialMotor.CreateKCubeInertialMotor(self.serial)
            self.device.Connect(self.serial)
            self.device.WaitForSettingsInitialized(5000)
            self.device.StartPolling(100)
            time.sleep(0.5)
            self.device.EnableDevice()
            time.sleep(0.3)
            
            self.channel = InertialMotorStatus.MotorChannels.Channel1
            self.log("Connect", True, f"Connected to {self.serial}")
            return True
        except Exception as e:
            self.log("Connect", False, str(e))
            return False
    
    def test_disconnect(self):
        """Test: Disconnect from Device"""
        print("\n" + "-" * 70)
        print("TEST: Disconnection")
        print("-" * 70)
        
        try:
            if self.device:
                self.device.StopPolling()
                self.device.Disconnect()
            self.log("Disconnect", True)
        except Exception as e:
            self.log("Disconnect", False, str(e))
    
    # =========================================================================
    # DEVICE INFO
    # =========================================================================
    
    def test_device_info(self):
        """Test: Get Device Information"""
        print("\n" + "-" * 70)
        print("TEST: Device Information")
        print("-" * 70)
        
        try:
            info = self.device.GetDeviceInfo()
            details = f"Name: {info.Name}\nDescription: {info.Description}\nSerial: {info.SerialNumber}"
            self.log("GetDeviceInfo", True, details)
        except Exception as e:
            self.log("GetDeviceInfo", False, str(e))
    
    def test_identify(self):
        """Test: Identify (LED Blink)"""
        print("\n" + "-" * 70)
        print("TEST: Identify (LED Blink)")
        print("-" * 70)
        
        try:
            self.device.IdentifyDevice()
            self.log("IdentifyDevice", True, "LED should blink on front panel")
            time.sleep(0.5)
        except Exception as e:
            self.log("IdentifyDevice", False, str(e))
    
    # =========================================================================
    # CHANNEL STATUS
    # =========================================================================
    
    def test_all_channels_status(self):
        """Test: Get Status for All 4 Channels"""
        print("\n" + "-" * 70)
        print("TEST: Channel Status (All 4 Channels)")
        print("-" * 70)
        
        channels = [
            ("Channel1", InertialMotorStatus.MotorChannels.Channel1),
            ("Channel2", InertialMotorStatus.MotorChannels.Channel2),
            ("Channel3", InertialMotorStatus.MotorChannels.Channel3),
            ("Channel4", InertialMotorStatus.MotorChannels.Channel4),
        ]
        
        for name, ch_enum in channels:
            try:
                status = self.device.Status[ch_enum]
                details = f"Pos={status.Position}, Moving={status.IsMoving}, Enabled={status.IsEnabled}"
                self.log(f"Status[{name}]", True, details)
            except Exception as e:
                self.log(f"Status[{name}]", False, str(e))
    
    # =========================================================================
    # DRIVE PARAMETERS
    # =========================================================================
    
    def test_drive_parameters(self):
        """Test: Get Drive Parameters"""
        print("\n" + "-" * 70)
        print("TEST: Get Drive Parameters")
        print("-" * 70)
        
        try:
            params = self.device.GetDriveParameters(self.channel)
            details = f"StepRate: {params.StepRate}\nStepAcceleration: {params.StepAcceleration}\nMaxVoltage: {params.MaxVoltage}"
            self.log("GetDriveParameters", True, details)
        except Exception as e:
            self.log("GetDriveParameters", False, str(e))
    
    def test_set_drive_parameters(self):
        """Test: Set Drive Parameters"""
        print("\n" + "-" * 70)
        print("TEST: Set Drive Parameters")
        print("-" * 70)
        
        try:
            # Get current
            params = self.device.GetDriveParameters(self.channel)
            original_rate = params.StepRate
            
            # Modify
            params.StepRate = 700
            self.device.SetDriveParameters(self.channel, params)
            
            # Verify
            params2 = self.device.GetDriveParameters(self.channel)
            success = params2.StepRate == 700
            
            # Restore
            params2.StepRate = original_rate
            self.device.SetDriveParameters(self.channel, params2)
            
            self.log("SetDriveParameters (StepRate)", success, f"Changed {original_rate} -> 700 -> {original_rate}")
        except Exception as e:
            self.log("SetDriveParameters", False, str(e))
        
        try:
            params = self.device.GetDriveParameters(self.channel)
            original_accel = params.StepAcceleration
            
            params.StepAcceleration = 5000
            self.device.SetDriveParameters(self.channel, params)
            
            params2 = self.device.GetDriveParameters(self.channel)
            success = params2.StepAcceleration == 5000
            
            params2.StepAcceleration = original_accel
            self.device.SetDriveParameters(self.channel, params2)
            
            self.log("SetDriveParameters (Acceleration)", success, f"Changed {original_accel} -> 5000 -> {original_accel}")
        except Exception as e:
            self.log("SetDriveParameters (Acceleration)", False, str(e))
    
    # =========================================================================
    # JOG PARAMETERS
    # =========================================================================
    
    def test_jog_parameters(self):
        """Test: Get Jog Parameters"""
        print("\n" + "-" * 70)
        print("TEST: Get Jog Parameters")
        print("-" * 70)
        
        try:
            jog = self.device.GetJogParameters(self.channel)
            details = f"JogStepFwd: {jog.JogStepFwd}\nJogStepRev: {jog.JogStepRev}\nJogRate: {jog.JogRate}\nJogAcceleration: {jog.JogAcceleration}"
            self.log("GetJogParameters", True, details)
        except Exception as e:
            self.log("GetJogParameters", False, str(e))
    
    def test_set_jog_parameters(self):
        """Test: Set Jog Parameters"""
        print("\n" + "-" * 70)
        print("TEST: Set Jog Parameters")
        print("-" * 70)
        
        try:
            jog = self.device.GetJogParameters(self.channel)
            original_fwd = jog.JogStepFwd
            
            jog.JogStepFwd = 200
            jog.JogStepRev = 200
            self.device.SetJogParameters(self.channel, jog)
            
            jog2 = self.device.GetJogParameters(self.channel)
            success = jog2.JogStepFwd == 200
            
            # Restore
            jog2.JogStepFwd = original_fwd
            jog2.JogStepRev = original_fwd
            self.device.SetJogParameters(self.channel, jog2)
            
            self.log("SetJogParameters", success, f"JogStepFwd: {original_fwd} -> 200 -> {original_fwd}")
        except Exception as e:
            self.log("SetJogParameters", False, str(e))
    
    # =========================================================================
    # CHANNEL ENABLE/DISABLE
    # =========================================================================
    
    def test_enable_disable_channel(self):
        """Test: Enable and Disable Channel"""
        print("\n" + "-" * 70)
        print("TEST: Enable/Disable Channel")
        print("-" * 70)
        
        try:
            # Enable
            self.device.EnableChannel(self.channel)
            time.sleep(0.2)
            status = self.device.Status[self.channel]
            enabled_after_enable = status.IsEnabled
            
            # Disable
            self.device.DisableChannel(self.channel)
            time.sleep(0.2)
            status = self.device.Status[self.channel]
            enabled_after_disable = status.IsEnabled
            
            # Re-enable for further tests
            self.device.EnableChannel(self.channel)
            time.sleep(0.2)
            
            success = enabled_after_enable and not enabled_after_disable
            self.log("EnableChannel", enabled_after_enable, f"IsEnabled={enabled_after_enable}")
            self.log("DisableChannel", not enabled_after_disable, f"IsEnabled={enabled_after_disable}")
        except Exception as e:
            self.log("Enable/Disable Channel", False, str(e))
    
    # =========================================================================
    # POSITION
    # =========================================================================
    
    def test_get_position(self):
        """Test: Get Position"""
        print("\n" + "-" * 70)
        print("TEST: Get Position")
        print("-" * 70)
        
        try:
            pos = self.device.GetPosition(self.channel)
            self.log("GetPosition", True, f"Position: {pos}")
        except Exception as e:
            self.log("GetPosition", False, str(e))
    
    def test_set_position_as_zero(self):
        """Test: Set Position As (Zero)"""
        print("\n" + "-" * 70)
        print("TEST: SetPositionAs (Zero)")
        print("-" * 70)
        
        try:
            self.device.SetPositionAs(self.channel, 0)
            time.sleep(0.2)
            pos = self.device.GetPosition(self.channel)
            success = pos == 0
            self.log("SetPositionAs(0)", success, f"Position after: {pos}")
        except Exception as e:
            self.log("SetPositionAs", False, str(e))
    
    # =========================================================================
    # JOG MOVEMENT
    # =========================================================================
    
    def test_jog_forward(self):
        """Test: Jog Forward (Increase)"""
        print("\n" + "-" * 70)
        print("TEST: Jog Forward (Increase)")
        print("-" * 70)
        
        try:
            pos_before = self.device.GetPosition(self.channel)
            self.device.Jog(self.channel, InertialMotorJogDirection.Increase, None)
            time.sleep(0.5)
            pos_after = self.device.GetPosition(self.channel)
            
            delta = pos_after - pos_before
            success = delta > 0
            self.log("Jog(Increase)", success, f"Position: {pos_before} -> {pos_after} (Δ={delta})")
        except Exception as e:
            self.log("Jog(Increase)", False, str(e))
    
    def test_jog_reverse(self):
        """Test: Jog Reverse (Decrease)"""
        print("\n" + "-" * 70)
        print("TEST: Jog Reverse (Decrease)")
        print("-" * 70)
        
        try:
            pos_before = self.device.GetPosition(self.channel)
            self.device.Jog(self.channel, InertialMotorJogDirection.Decrease, None)
            time.sleep(0.5)
            pos_after = self.device.GetPosition(self.channel)
            
            delta = pos_after - pos_before
            success = delta < 0
            self.log("Jog(Decrease)", success, f"Position: {pos_before} -> {pos_after} (Δ={delta})")
        except Exception as e:
            self.log("Jog(Decrease)", False, str(e))
    
    # =========================================================================
    # MOVE BY / MOVE TO
    # =========================================================================
    
    def test_move_by_positive(self):
        """Test: MoveBy (positive steps)"""
        print("\n" + "-" * 70)
        print("TEST: MoveBy (+500 steps)")
        print("-" * 70)
        
        try:
            pos_before = self.device.GetPosition(self.channel)
            self.device.MoveBy(self.channel, 500, None)  # Async
            time.sleep(0.8)
            pos_after = self.device.GetPosition(self.channel)
            
            delta = pos_after - pos_before
            success = delta > 0
            self.log("MoveBy(+500)", success, f"Position: {pos_before} -> {pos_after} (Δ={delta})")
        except Exception as e:
            self.log("MoveBy(+500)", False, str(e))
    
    def test_move_by_negative(self):
        """Test: MoveBy (negative steps)"""
        print("\n" + "-" * 70)
        print("TEST: MoveBy (-500 steps)")
        print("-" * 70)
        
        try:
            pos_before = self.device.GetPosition(self.channel)
            self.device.MoveBy(self.channel, -500, None)  # Async
            time.sleep(0.8)
            pos_after = self.device.GetPosition(self.channel)
            
            delta = pos_after - pos_before
            success = delta < 0
            self.log("MoveBy(-500)", success, f"Position: {pos_before} -> {pos_after} (Δ={delta})")
        except Exception as e:
            self.log("MoveBy(-500)", False, str(e))
    
    def test_move_to(self):
        """Test: MoveTo (absolute position)"""
        print("\n" + "-" * 70)
        print("TEST: MoveTo (position 1000)")
        print("-" * 70)
        
        try:
            pos_before = self.device.GetPosition(self.channel)
            self.device.MoveTo(self.channel, 1000, None)  # Async
            time.sleep(1)
            pos_after = self.device.GetPosition(self.channel)
            
            # Should have moved toward 1000
            moved = pos_after != pos_before
            self.log("MoveTo(1000)", moved, f"Position: {pos_before} -> {pos_after}")
        except Exception as e:
            self.log("MoveTo(1000)", False, str(e))
    
    # =========================================================================
    # STOP & STATUS
    # =========================================================================
    
    def test_stop(self):
        """Test: Stop"""
        print("\n" + "-" * 70)
        print("TEST: Stop")
        print("-" * 70)
        
        try:
            self.device.Stop(self.channel)
            self.log("Stop", True, "Stop command sent")
        except Exception as e:
            self.log("Stop", False, str(e))
    
    def test_is_moving(self):
        """Test: Check IsMoving status"""
        print("\n" + "-" * 70)
        print("TEST: IsMoving Check")
        print("-" * 70)
        
        try:
            status = self.device.Status[self.channel]
            self.log("IsMoving", True, f"IsMoving: {status.IsMoving}")
        except Exception as e:
            self.log("IsMoving", False, str(e))
    
    # =========================================================================
    # MULTI-CHANNEL
    # =========================================================================
    
    def test_multi_channel(self):
        """Test: Multi-Channel Operation (Channel 2)"""
        print("\n" + "-" * 70)
        print("TEST: Multi-Channel (Channel 2)")
        print("-" * 70)
        
        channel2 = InertialMotorStatus.MotorChannels.Channel2
        
        try:
            # Get status
            status = self.device.Status[channel2]
            self.log("Channel2 Status", True, f"Pos={status.Position}, Enabled={status.IsEnabled}")
            
            # Enable
            self.device.EnableChannel(channel2)
            time.sleep(0.2)
            
            # Jog
            pos_before = self.device.GetPosition(channel2)
            self.device.Jog(channel2, InertialMotorJogDirection.Increase, None)
            time.sleep(0.5)
            pos_after = self.device.GetPosition(channel2)
            
            delta = pos_after - pos_before
            self.log("Channel2 Jog", True, f"Position: {pos_before} -> {pos_after} (Δ={delta})")
        except Exception as e:
            self.log("Channel2", False, str(e))
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        total = self.passed + self.failed
        print(f"\n  Total Tests: {total}")
        print(f"  Passed:      {self.passed}")
        print(f"  Failed:      {self.failed}")
        
        if self.failed > 0:
            print("\n  Failed Tests:")
            for name, passed, details in self.results:
                if not passed:
                    print(f"    - {name}")
        
        print("\n" + "=" * 70)
        if self.failed == 0:
            print("  *** ALL TESTS PASSED ***")
        else:
            print(f"  *** {self.failed} TEST(S) FAILED ***")
        print("=" * 70)


def main():
    suite = KIM101TestSuite()
    success = suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
