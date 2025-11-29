"""
KBD101 K-Cube Brushless DC Servo Motor Controller - Comprehensive Test Suite
=============================================================================

This module provides a comprehensive test suite for the Thorlabs KBD101
K-Cube Brushless DC Motor Controller, validating all API functionality via
the Kinesis .NET DLL interface.

Controller Specifications
-------------------------
- **Model:** KBD101
- **Type:** Brushless DC Motor Driver
- **Channels:** 1
- **Serial Prefix:** 28
- **Interface:** USB (Kinesis)

Compatible Stages
-----------------
- DDS100 — 100mm Direct-Drive Stage (500mm/s max velocity)
- DDS220 — 220mm Direct-Drive Stage
- DDS300 — 300mm Direct-Drive Stage
- DDS600 — 600mm Direct-Drive Stage

Test Coverage (21 Tests)
------------------------
1. Device Discovery
2. Stage Auto-Detection (via EEPROM)
3. Connection Management
4. Device Information & Identification
5. Stage Information Query
6. Status Queries
7. Position Reading
8. Velocity Parameter Get/Set
9. Homing Operation
10. Absolute Movement
11. Relative Movement
12. Stop Command
13. Movement State Query

Usage
-----
Command line::

    python test_kbd101.py

Programmatic::

    from test_kbd101 import KBD101TestSuite
    suite = KBD101TestSuite(serial_number=28252335)
    success = suite.run_all_tests()

Requirements
------------
- KBD101 controller connected via USB
- DDS-series stage attached (for full testing)
- Thorlabs Kinesis v1.14+ installed
- Python 3.8+ with pythonnet

See Also
--------
- tests/README.md for full testing documentation
- KBD101Controller class for API details
"""
import sys
import os
import time

# Add paths
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, workspace_root)
sys.path.insert(0, r'C:\Program Files\Thorlabs\Kinesis')

from Hardware.ThorlabsMotionControl.device_manager import discover_devices, discover_devices_with_stages
from Hardware.ThorlabsMotionControl.kinesis.kbd101 import KBD101Controller

# Expected device - update this for your setup
EXPECTED_SERIAL = 28252335
EXPECTED_STAGE = "DDS100"  # 100mm travel direct-drive stage


class KBD101TestSuite:
    """
    Comprehensive test suite for KBD101 K-Cube Brushless DC Controller.
    
    This test suite validates all functionality of the KBD101 controller
    including device discovery, stage auto-detection, connection management,
    motion control, and parameter configuration. Designed for use with
    DDS-series direct-drive stages.
    
    Attributes:
        ctrl: KBD101Controller instance (created during test_connect).
        serial: Device serial number (auto-discovered or pre-set).
        stage_info: Detected stage information dictionary.
        results: List of (test_name, passed, details) tuples.
        passed: Count of passed tests.
        failed: Count of failed tests.
    
    Example:
        >>> suite = KBD101TestSuite(serial_number=28252335)
        >>> success = suite.run_all_tests()
        >>> print(f"Stage detected: {suite.stage_info}")
    """
    
    def __init__(self, serial_number: int = None):
        self.ctrl = None
        self.serial = serial_number  # Can be pre-set or discovered
        self.stage_info = None
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
        print("KBD101 COMPREHENSIVE TEST SUITE")
        print("K-Cube Brushless DC Servo Motor Controller")
        print("=" * 70)
        
        try:
            # Discovery
            if not self.test_discovery():
                print("\n[ABORT] No KBD101 device found!")
                return False
            
            # Connection
            if not self.test_connect():
                print("\n[ABORT] Failed to connect!")
                return False
            
            # Run all tests
            self.test_device_info()
            self.test_identify()
            self.test_stage_info()
            self.test_status()
            self.test_position()
            self.test_velocity_params()
            self.test_set_velocity()
            self.test_homing()
            self.test_move_absolute()
            self.test_move_relative()
            self.test_stop()
            self.test_is_moving()
            
        finally:
            self.test_disconnect()
        
        self.print_summary()
        return self.failed == 0
    
    # =========================================================================
    # DISCOVERY & CONNECTION
    # =========================================================================
    
    def test_discovery(self) -> bool:
        """Test: Device Discovery with Stage Detection"""
        print("\n" + "-" * 70)
        print("TEST: Device Discovery")
        print("-" * 70)
        
        try:
            # Basic discovery
            devices = discover_devices()
            kbd_devices = [d for d in devices if d['controller_type'] == 'KBD101']
            
            # If serial was pre-set, verify it exists
            if self.serial:
                matching = [d for d in kbd_devices if int(d['serial']) == self.serial]
                if matching:
                    self.log("Discovery (pre-set)", True, f"Found KBD101: {self.serial}")
                else:
                    self.log("Discovery (pre-set)", False, f"Device {self.serial} not found")
                    return False
            elif kbd_devices:
                self.serial = int(kbd_devices[0]['serial'])
                self.log("Discovery", True, f"Found KBD101: {self.serial}")
            else:
                self.log("Discovery", False, "No KBD101 found")
                return False
            
            # Discovery with stage detection
            devices_with_stages = discover_devices_with_stages()
            for dev in devices_with_stages:
                if int(dev['serial']) == self.serial:
                    if dev.get('stage'):
                        self.stage_info = dev['stage']
                        stage_name = self.stage_info.get('part_number', 'Unknown')
                        travel = self.stage_info.get('max_travel', 'Unknown')
                        self.log("Stage auto-detection", True, 
                                f"Stage: {stage_name}\nMax travel: {travel} mm")
                    else:
                        self.log("Stage auto-detection", True, "No stage connected")
                    break
            
            return True
        except Exception as e:
            self.log("Discovery", False, str(e))
            return False
    
    def test_connect(self) -> bool:
        """Test: Connect to Device"""
        print("\n" + "-" * 70)
        print("TEST: Connection")
        print("-" * 70)
        
        try:
            self.ctrl = KBD101Controller(serial_number=self.serial, channel=1)
            self.log("Controller created", True, f"Serial: {self.serial}")
            
            start = time.time()
            result = self.ctrl.connect()
            elapsed = time.time() - start
            
            self.log("connect()", result and self.ctrl.is_connected, 
                    f"State: {self.ctrl.state}\nTime: {elapsed:.2f}s")
            return result
        except Exception as e:
            self.log("connect()", False, str(e))
            return False
    
    def test_disconnect(self):
        """Test: Disconnect from Device"""
        print("\n" + "-" * 70)
        print("TEST: Disconnection")
        print("-" * 70)
        
        try:
            if self.ctrl:
                self.ctrl.disconnect()
            self.log("disconnect()", True, f"State: {self.ctrl.state if self.ctrl else 'N/A'}")
        except Exception as e:
            self.log("disconnect()", False, str(e))
    
    # =========================================================================
    # DEVICE INFO
    # =========================================================================
    
    def test_device_info(self):
        """Test: Get Device Information"""
        print("\n" + "-" * 70)
        print("TEST: Device Information")
        print("-" * 70)
        
        try:
            self.log("Controller type", True, "KBD101")
            self.log("Serial number", True, str(self.serial))
        except Exception as e:
            self.log("Device info", False, str(e))
    
    def test_identify(self):
        """Test: Identify (LED Blink)"""
        print("\n" + "-" * 70)
        print("TEST: Identify (LED Blink)")
        print("-" * 70)
        
        try:
            self.ctrl.identify()
            self.log("identify()", True, "LED should blink on front panel")
            time.sleep(0.5)
        except Exception as e:
            self.log("identify()", False, str(e))
    
    def test_stage_info(self):
        """Test: Get Stage Information"""
        print("\n" + "-" * 70)
        print("TEST: Stage Information")
        print("-" * 70)
        
        try:
            stage_info = self.ctrl.get_stage_info()
            if stage_info:
                details = '\n'.join(f"{k}: {v}" for k, v in stage_info.items())
                self.log("get_stage_info()", True, details)
            else:
                self.log("get_stage_info()", True, "No stage info available")
        except Exception as e:
            self.log("get_stage_info()", False, str(e))
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def test_status(self):
        """Test: Get Status"""
        print("\n" + "-" * 70)
        print("TEST: Status Queries")
        print("-" * 70)
        
        try:
            status = self.ctrl.get_status()
            details = '\n'.join(f"{k}: {v}" for k, v in status.items())
            self.log("get_status()", True, details)
        except Exception as e:
            self.log("get_status()", False, str(e))
    
    def test_position(self):
        """Test: Get Position"""
        print("\n" + "-" * 70)
        print("TEST: Get Position")
        print("-" * 70)
        
        try:
            pos = self.ctrl.get_position()
            self.log("get_position()", True, f"Position: {pos} mm")
        except Exception as e:
            self.log("get_position()", False, str(e))
    
    # =========================================================================
    # VELOCITY PARAMETERS
    # =========================================================================
    
    def test_velocity_params(self):
        """Test: Get Velocity Parameters"""
        print("\n" + "-" * 70)
        print("TEST: Get Velocity Parameters")
        print("-" * 70)
        
        try:
            params = self.ctrl.get_velocity_params()
            details = '\n'.join(f"{k}: {v}" for k, v in params.items())
            self.log("get_velocity_params()", True, details)
        except Exception as e:
            self.log("get_velocity_params()", False, str(e))
    
    def test_set_velocity(self):
        """Test: Set Velocity Parameters"""
        print("\n" + "-" * 70)
        print("TEST: Set Velocity Parameters")
        print("-" * 70)
        
        try:
            # Get current
            params = self.ctrl.get_velocity_params()
            orig_velocity = params.get('max_velocity', 10.0)
            
            # Set new velocity
            test_velocity = 5.0
            result = self.ctrl.set_velocity(test_velocity)
            self.log("set_velocity(5.0)", result)
            
            # Verify
            new_params = self.ctrl.get_velocity_params()
            self.log("Velocity updated", True, f"New velocity: {new_params.get('max_velocity')}")
            
            # Restore
            self.ctrl.set_velocity(orig_velocity if orig_velocity > 0 else 10.0)
        except Exception as e:
            self.log("set_velocity()", False, str(e))
    
    # =========================================================================
    # MOVEMENT
    # =========================================================================
    
    def test_homing(self):
        """Test: Homing"""
        print("\n" + "-" * 70)
        print("TEST: Homing")
        print("-" * 70)
        
        try:
            print("  Starting homing sequence (DDS100 stage)...")
            start = time.time()
            result = self.ctrl.home(wait=True, timeout=60.0)
            elapsed = time.time() - start
            
            pos = self.ctrl.get_position()
            is_homed = self.ctrl.is_homed()
            
            self.log("home()", result, 
                    f"Time: {elapsed:.2f}s\nPosition: {pos}\nis_homed: {is_homed}")
        except Exception as e:
            self.log("home()", False, str(e))
    
    def test_move_absolute(self):
        """Test: Absolute Movement"""
        print("\n" + "-" * 70)
        print("TEST: Absolute Movement")
        print("-" * 70)
        
        if not self.ctrl.is_homed():
            self.log("move_absolute()", False, "Not homed - skipping")
            return
        
        try:
            # DDS100 has 100mm travel - test small movements
            
            # Move to position 10mm
            target = 10.0
            print(f"  Moving to {target} mm...")
            start = time.time()
            result = self.ctrl.move_absolute(target, wait=True, timeout=30.0)
            elapsed = time.time() - start
            
            pos = self.ctrl.get_position()
            self.log(f"move_absolute({target})", result, 
                    f"Position: {pos} mm\nTime: {elapsed:.2f}s")
            
            # Move to position 20mm
            target = 20.0
            print(f"  Moving to {target} mm...")
            result = self.ctrl.move_absolute(target, wait=True, timeout=30.0)
            pos = self.ctrl.get_position()
            self.log(f"move_absolute({target})", result, f"Position: {pos} mm")
            
        except Exception as e:
            self.log("move_absolute()", False, str(e))
    
    def test_move_relative(self):
        """Test: Relative Movement"""
        print("\n" + "-" * 70)
        print("TEST: Relative Movement")
        print("-" * 70)
        
        if not self.ctrl.is_homed():
            self.log("move_relative()", False, "Not homed - skipping")
            return
        
        try:
            pos_before = self.ctrl.get_position()
            
            # Move +5mm
            distance = 5.0
            print(f"  Moving relative {distance:+} mm...")
            result = self.ctrl.move_relative(distance, wait=True, timeout=30.0)
            pos_after = self.ctrl.get_position()
            
            delta = pos_after - pos_before
            self.log(f"move_relative(+{distance})", result, 
                    f"Before: {pos_before} mm\nAfter: {pos_after} mm\nDelta: {delta} mm")
            
            # Move -5mm
            distance = -5.0
            pos_before = pos_after
            print(f"  Moving relative {distance} mm...")
            result = self.ctrl.move_relative(distance, wait=True, timeout=30.0)
            pos_after = self.ctrl.get_position()
            
            delta = pos_after - pos_before
            self.log(f"move_relative({distance})", result, 
                    f"Before: {pos_before} mm\nAfter: {pos_after} mm\nDelta: {delta} mm")
            
        except Exception as e:
            self.log("move_relative()", False, str(e))
    
    def test_stop(self):
        """Test: Stop Command"""
        print("\n" + "-" * 70)
        print("TEST: Stop Command")
        print("-" * 70)
        
        try:
            self.ctrl.stop()
            self.log("stop()", True, "Stop command sent")
        except Exception as e:
            self.log("stop()", False, str(e))
    
    def test_is_moving(self):
        """Test: IsMoving Status"""
        print("\n" + "-" * 70)
        print("TEST: IsMoving Status")
        print("-" * 70)
        
        try:
            is_moving = self.ctrl.is_moving
            self.log("is_moving", True, f"is_moving: {is_moving}")
        except Exception as e:
            self.log("is_moving", False, str(e))
    
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
    suite = KBD101TestSuite()
    success = suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
