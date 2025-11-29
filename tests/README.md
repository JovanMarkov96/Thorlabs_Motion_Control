# ThorlabsMotionControl Test Suite

Comprehensive hardware validation tests for Thorlabs motion control devices.

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Runner](#test-runner)
- [Individual Test Suites](#individual-test-suites)
- [Test Coverage](#test-coverage)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)

---

## Overview

The test suite provides comprehensive validation of all controller functionality, including:

- **Device Discovery** — Verify devices can be found on USB
- **Connection Management** — Connect, disconnect, reconnect
- **Device Identification** — LED blink, device info queries
- **Stage Detection** — Auto-detect connected stages via EEPROM
- **Status Queries** — Position, velocity, movement state
- **Motion Control** — Homing, absolute moves, relative moves
- **Parameter Configuration** — Velocity, acceleration settings
- **Emergency Stop** — Stop command functionality

### Test Statistics

| Metric | Value |
|--------|-------|
| Total Test Suites | 4 |
| Total Tests | 88 |
| Controllers Covered | KDC101, KBD101, TDC001, KIM101 |
| API Coverage | 100% of public methods |

---

## Quick Start

### Prerequisites

1. **Hardware Connected** — Connect Thorlabs controllers via USB
2. **Kinesis Installed** — Thorlabs Kinesis software must be installed
3. **Python Environment** — Python 3.8+ with pythonnet

### List Connected Devices

```bash
python run_all_tests.py --list
```

Output:
```
======================================================================
  THORLABS MOTION CONTROL - MASTER TEST RUNNER
======================================================================

Scanning for connected devices...

  Found 4 device(s):

  ------------------------------------------------------------------
  #    Type       Serial       Stage                Test
  ------------------------------------------------------------------
  1    KDC101     27503318     -                    Yes
  2    KBD101     28252335     DDS100               Yes
  3    TDC001     83863609     -                    Yes
  4    KIM101     97101306     -                    Yes
  ------------------------------------------------------------------
```

### Run All Tests

```bash
python run_all_tests.py
```

---

## Test Runner

### Command Line Interface

```bash
python run_all_tests.py [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--list` | `-l` | List connected devices without testing |
| `--select` | `-s` | Interactive device selection mode |
| `--type TYPE` | `-t` | Filter by device type (KDC, KBD, TDC, KIM) |

### Examples

```bash
# List all connected devices
python run_all_tests.py --list

# Test all connected devices
python run_all_tests.py

# Test only KIM101 devices
python run_all_tests.py --type KIM

# Test only DC servo controllers
python run_all_tests.py --type KDC

# Interactive selection
python run_all_tests.py --select
```

### Running from Package Root

```bash
# From the workspace root
python -m Hardware.ThorlabsMotionControl.tests.run_all_tests --list
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |

---

## Individual Test Suites

### test_kdc101.py — K-Cube DC Servo Controller

**Controller:** KDC101  
**Serial Prefix:** 27  
**Compatible Stages:** PRM1Z8, Z825B, MTS25-Z8, MTS50-Z8, etc.

| # | Test | Description |
|---|------|-------------|
| 1 | Discovery | Find KDC101 on USB |
| 2 | Controller Created | Instantiate controller object |
| 3 | connect() | Establish connection |
| 4 | Controller Type | Verify type identification |
| 5 | Serial Number | Verify serial number |
| 6 | identify() | LED blink test |
| 7 | get_stage_info() | Query connected stage |
| 8 | get_status() | Comprehensive status query |
| 9 | get_position() | Current position reading |
| 10 | get_velocity_params() | Velocity settings query |
| 11 | set_velocity() | Modify velocity |
| 12 | Velocity Updated | Verify velocity change |
| 13 | home() | Homing sequence |
| 14 | move_absolute(5.0) | Move to position 5 |
| 15 | move_absolute(10.0) | Move to position 10 |
| 16 | move_relative(+2.0) | Relative forward move |
| 17 | move_relative(-2.0) | Relative reverse move |
| 18 | stop() | Stop command |
| 19 | is_moving | Movement state query |
| 20 | disconnect() | Close connection |

**Run individually:**
```bash
python test_kdc101.py
```

---

### test_kbd101.py — K-Cube Brushless DC Controller

**Controller:** KBD101  
**Serial Prefix:** 28  
**Compatible Stages:** DDS100, DDS220, DDS300, DDS600

| # | Test | Description |
|---|------|-------------|
| 1 | Discovery | Find KBD101 on USB |
| 2 | Discovery (pre-set) | Find specific serial |
| 3 | Stage auto-detection | Detect DDS stage via EEPROM |
| 4 | Controller Created | Instantiate controller |
| 5 | connect() | Establish connection |
| 6 | Controller Type | Verify type |
| 7 | Serial Number | Verify serial |
| 8 | identify() | LED blink |
| 9 | get_stage_info() | Query DDS stage info |
| 10 | get_status() | Status query |
| 11 | get_position() | Position reading (mm) |
| 12 | get_velocity_params() | Velocity query |
| 13 | set_velocity() | Modify velocity |
| 14 | Velocity Updated | Verify change |
| 15 | home() | Homing (DDS100 specific) |
| 16 | move_absolute(10.0) | Move to 10mm |
| 17 | move_absolute(20.0) | Move to 20mm |
| 18 | move_relative(+5.0) | Forward 5mm |
| 19 | move_relative(-5.0) | Reverse 5mm |
| 20 | stop() | Stop command |
| 21 | is_moving | Movement state |
| 22 | disconnect() | Close connection |

**Run individually:**
```bash
python test_kbd101.py
```

---

### test_tdc001.py — T-Cube DC Servo Controller (Legacy)

**Controller:** TDC001  
**Serial Prefix:** 83  
**Compatible Stages:** Same as KDC101

| # | Test | Description |
|---|------|-------------|
| 1-20 | Same as KDC101 | Identical test structure |

**Run individually:**
```bash
python test_tdc001.py
```

---

### test_kim101.py — K-Cube Inertial Motor Controller

**Controller:** KIM101  
**Serial Prefix:** 97  
**Channels:** 4  
**Compatible Actuators:** PIA13, PIA25, PIA50, PIAK10, PIAK25

| # | Test | Description |
|---|------|-------------|
| 1 | Discovery | Find KIM101 on USB |
| 2 | Connect | Establish connection |
| 3 | GetDeviceInfo | Query device information |
| 4 | IdentifyDevice | LED blink |
| 5 | Status[Channel1] | Channel 1 status |
| 6 | Status[Channel2] | Channel 2 status |
| 7 | Status[Channel3] | Channel 3 status |
| 8 | Status[Channel4] | Channel 4 status |
| 9 | GetDriveParameters | Drive params query |
| 10 | SetDriveParameters (StepRate) | Modify step rate |
| 11 | SetDriveParameters (Acceleration) | Modify acceleration |
| 12 | GetJogParameters | Jog params query |
| 13 | SetJogParameters | Modify jog params |
| 14 | EnableChannel | Enable channel |
| 15 | DisableChannel | Disable channel |
| 16 | GetPosition | Position query |
| 17 | SetPositionAs(0) | Zero position |
| 18 | Jog(Increase) | Jog forward |
| 19 | Jog(Decrease) | Jog reverse |
| 20 | MoveBy(+500) | Relative +500 steps |
| 21 | MoveBy(-500) | Relative -500 steps |
| 22 | MoveTo(1000) | Move to position 1000 |
| 23 | Stop | Stop command |
| 24 | IsMoving | Movement state |
| 25 | Channel2 Status | Multi-channel test |
| 26 | Channel2 Jog | Multi-channel jog |
| 27 | Disconnect | Close connection |

**Run individually:**
```bash
python test_kim101.py
```

---

## Test Coverage

### API Coverage Matrix

| Method | KDC101 | KBD101 | TDC001 | KIM101 |
|--------|--------|--------|--------|--------|
| `connect()` | ✅ | ✅ | ✅ | ✅ |
| `disconnect()` | ✅ | ✅ | ✅ | ✅ |
| `identify()` | ✅ | ✅ | ✅ | ✅ |
| `get_status()` | ✅ | ✅ | ✅ | ✅ |
| `get_position()` | ✅ | ✅ | ✅ | ✅ |
| `home()` | ✅ | ✅ | ✅ | N/A |
| `move_absolute()` | ✅ | ✅ | ✅ | ✅ |
| `move_relative()` | ✅ | ✅ | ✅ | ✅ |
| `stop()` | ✅ | ✅ | ✅ | ✅ |
| `get_velocity_params()` | ✅ | ✅ | ✅ | ✅ |
| `set_velocity()` | ✅ | ✅ | ✅ | ✅ |
| `is_homed()` | ✅ | ✅ | ✅ | N/A |
| `get_stage_info()` | ✅ | ✅ | ✅ | N/A |
| `jog()` | N/A | N/A | N/A | ✅ |
| Multi-channel | N/A | N/A | N/A | ✅ |

### Results Summary

After a full test run, the runner displays:

```
======================================================================
  FINAL TEST SUMMARY
======================================================================

  Device     Serial       Tests      Passed     Failed     Status
  --------------------------------------------------------------
  KDC101     27503318     20         20         0          PASS
  KBD101     28252335     21         21         0          PASS
  TDC001     83863609     20         20         0          PASS
  KIM101     97101306     27         27         0          PASS
  --------------------------------------------------------------

  Total Devices: 4
  Devices Passed: 4
  Devices Failed: 0

  Total Tests: 88
  Tests Passed: 88
  Tests Failed: 0

======================================================================
  *** ALL DEVICES PASSED ALL TESTS ***
======================================================================
```

---

## Writing Tests

### Test Suite Template

```python
"""
<CONTROLLER> <Description> - Comprehensive Test Suite
======================================================

Tests all <CONTROLLER> functionality via Kinesis DLL.

Run: python test_<controller>.py
"""
import sys
import os
import time

# Path setup
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, workspace_root)
sys.path.insert(0, r'C:\Program Files\Thorlabs\Kinesis')

from Hardware.ThorlabsMotionControl.device_manager import discover_devices
from Hardware.ThorlabsMotionControl.kinesis.<controller> import <Controller>Controller


class <Controller>TestSuite:
    """Comprehensive test suite for <CONTROLLER> controller."""
    
    def __init__(self, serial_number: int = None):
        self.ctrl = None
        self.serial = serial_number
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
        print("<CONTROLLER> COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        
        try:
            if not self.test_discovery():
                return False
            if not self.test_connect():
                return False
            
            # Run functionality tests
            self.test_identify()
            self.test_status()
            # ... more tests ...
            
        finally:
            self.test_disconnect()
        
        self.print_summary()
        return self.failed == 0
    
    # Test methods...
    
    def print_summary(self):
        """Print test summary."""
        print(f"\n  Total: {self.passed + self.failed}")
        print(f"  Passed: {self.passed}")
        print(f"  Failed: {self.failed}")


def main():
    suite = <Controller>TestSuite()
    return 0 if suite.run_all_tests() else 1


if __name__ == "__main__":
    sys.exit(main())
```

### Test Method Pattern

```python
def test_<name>(self):
    """Test: <Description>"""
    print("\n" + "-" * 70)
    print("TEST: <Description>")
    print("-" * 70)
    
    try:
        # Test logic
        result = self.ctrl.some_method()
        
        # Verify result
        self.log("<method>()", result, f"Details: {result}")
        
    except Exception as e:
        self.log("<method>()", False, str(e))
```

---

## Troubleshooting

### Common Issues

#### Device Not Found

```
[FAIL] Discovery
       No KDC101 found
```

**Solutions:**
1. Check USB connection
2. Verify device in Kinesis software
3. Power cycle the controller
4. Check Windows Device Manager

#### Connection Timeout

```
[FAIL] connect()
       Connection timeout
```

**Solutions:**
1. Close Kinesis software
2. Disconnect other applications
3. Increase timeout: `ctrl.connect(timeout=10.0)`
4. Power cycle device

#### Homing Timeout

```
[FAIL] home()
       Homing timeout
```

**Solutions:**
1. Check stage is properly attached
2. Verify stage type matches controller
3. Increase timeout: `ctrl.home(timeout=120.0)`
4. Check for mechanical obstructions

#### Import Error

```
ModuleNotFoundError: No module named 'clr'
```

**Solutions:**
1. Install pythonnet: `pip install pythonnet`
2. Verify 64-bit Python for Kinesis backend
3. Check Kinesis installation path

### Debug Mode

For detailed debugging, modify test to print more info:

```python
try:
    status = self.ctrl.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
except Exception as e:
    import traceback
    traceback.print_exc()
```

---

## Files Reference

```
tests/
├── README.md           # This documentation
├── __init__.py         # Package marker with exports
├── run_all_tests.py    # Master test runner
├── test_kdc101.py      # KDC101 test suite (20 tests)
├── test_kbd101.py      # KBD101 test suite (21 tests)
├── test_tdc001.py      # TDC001 test suite (20 tests)
└── test_kim101.py      # KIM101 test suite (27 tests)
```

---

## See Also

- [Main README](../README.md) — Package documentation
- [CONTRIBUTING](../CONTRIBUTING.md) — Contribution guidelines
