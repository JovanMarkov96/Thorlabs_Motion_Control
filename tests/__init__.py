"""
ThorlabsMotionControl Test Suite
================================

Comprehensive hardware validation tests for Thorlabs motion control devices.

This package provides test suites for all supported controllers:

Test Suites
-----------
- **test_kdc101** — K-Cube DC Servo Motor Controller (20 tests)
- **test_kbd101** — K-Cube Brushless DC Motor Controller (21 tests)
- **test_tdc001** — T-Cube DC Servo Motor Controller (20 tests)
- **test_kim101** — K-Cube Inertial Motor Controller (27 tests)

Master Test Runner
------------------
- **run_all_tests** — Discovers devices and runs appropriate tests

Quick Start
-----------
List connected devices::

    python -m Hardware.ThorlabsMotionControl.tests.run_all_tests --list

Run all tests::

    python -m Hardware.ThorlabsMotionControl.tests.run_all_tests

Test specific device type::

    python -m Hardware.ThorlabsMotionControl.tests.run_all_tests --type KIM

Programmatic Usage
------------------
Run tests programmatically::

    from Hardware.ThorlabsMotionControl.tests import (
        KDC101TestSuite,
        KBD101TestSuite,
        TDC001TestSuite,
        KIM101TestSuite,
    )
    
    # Test a specific device
    suite = KDC101TestSuite(serial_number=27503318)
    success = suite.run_all_tests()

Test Requirements
-----------------
- Hardware must be connected via USB
- Thorlabs Kinesis software must be installed
- Python 3.8+ with pythonnet

See Also
--------
- tests/README.md — Detailed testing documentation
- CONTRIBUTING.md — Guidelines for adding new tests

"""

# Lazy imports to avoid loading Kinesis DLLs until needed
__all__ = [
    "KDC101TestSuite",
    "KBD101TestSuite", 
    "TDC001TestSuite",
    "KIM101TestSuite",
    "run_all_tests",
]


def __getattr__(name):
    """Lazy import test suites to avoid loading DLLs at import time."""
    if name == "KDC101TestSuite":
        from .test_kdc101 import KDC101TestSuite
        return KDC101TestSuite
    elif name == "KBD101TestSuite":
        from .test_kbd101 import KBD101TestSuite
        return KBD101TestSuite
    elif name == "TDC001TestSuite":
        from .test_tdc001 import TDC001TestSuite
        return TDC001TestSuite
    elif name == "KIM101TestSuite":
        from .test_kim101 import KIM101TestSuite
        return KIM101TestSuite
    elif name == "run_all_tests":
        from . import run_all_tests
        return run_all_tests
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
