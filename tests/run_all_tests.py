"""
ThorlabsMotionControl - Master Test Runner
==========================================

Discovers all connected Thorlabs devices and runs comprehensive test suites
on each device. Supports multiple devices of the same type and provides
automatic test suite selection based on device type.

Features
--------
- **Auto-Discovery**: Automatically detects all connected Thorlabs USB devices
- **Smart Routing**: Routes each device to its appropriate test suite
- **Multi-Device**: Supports testing multiple devices in a single run
- **Filtering**: Test specific device types or interactively select devices
- **Comprehensive Reporting**: Detailed per-device and aggregate results

Supported Controllers
---------------------
- **KDC101**: K-Cube DC Servo Motor Controller (20 tests)
- **KBD101**: K-Cube Brushless DC Motor Controller (21 tests)
- **TDC001**: T-Cube DC Servo Motor Controller - Legacy (20 tests)
- **KIM101**: K-Cube Piezo Inertial Motor Controller (27 tests)

Command Line Usage
------------------
.. code-block:: bash

    # Test all connected devices
    python run_all_tests.py
    
    # List devices without testing
    python run_all_tests.py --list
    
    # Interactive device selection
    python run_all_tests.py --select
    
    # Test only specific device type
    python run_all_tests.py --type KIM
    python run_all_tests.py --type KDC

Programmatic Usage
------------------
.. code-block:: python

    from tests.run_all_tests import discover_all_devices, run_test_for_device
    
    # Discover connected devices
    devices = discover_all_devices()
    
    # Run tests on specific device
    result = run_test_for_device(devices[0])
    print(f"Passed: {result['passed']}, Failed: {result['failed']}")

Exit Codes
----------
- 0: All tests passed
- 1: One or more tests failed or error occurred

Requirements
------------
- Thorlabs Kinesis software installed (C:\\Program Files\\Thorlabs\\Kinesis)
- pythonnet package for .NET interop
- At least one connected Thorlabs motion controller

Author
------
Weizmann Institute Ion Trap Lab

See Also
--------
- test_kdc101.py : KDC101 test suite
- test_kbd101.py : KBD101 test suite  
- test_tdc001.py : TDC001 test suite
- test_kim101.py : KIM101 test suite
"""
import sys
import os
import argparse
import time
from typing import List, Dict, Optional

# Add paths FIRST - before any imports
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
    
kinesis_path = r'C:\Program Files\Thorlabs\Kinesis'
if kinesis_path not in sys.path:
    sys.path.insert(0, kinesis_path)

# Now import pythonnet (clr) to initialize .NET runtime
import clr

# Now safe to import our modules
from Hardware.ThorlabsMotionControl.device_manager import discover_devices, discover_devices_with_stages

# Import test suites (lazy import to avoid initialization issues)
_test_suites_loaded = False
KDC101TestSuite = None
KBD101TestSuite = None
KIM101TestSuite = None
TDC001TestSuite = None


def _load_test_suites():
    """
    Lazy load test suites to ensure paths are set up correctly.
    
    This function defers importing test suite classes until they are
    actually needed, ensuring that all path setup (workspace root,
    Kinesis DLLs) is complete before imports occur.
    """
    global _test_suites_loaded, KDC101TestSuite, KBD101TestSuite, KIM101TestSuite, TDC001TestSuite
    if _test_suites_loaded:
        return
    
    from Hardware.ThorlabsMotionControl.tests.test_kdc101 import KDC101TestSuite as _KDC101
    from Hardware.ThorlabsMotionControl.tests.test_kbd101 import KBD101TestSuite as _KBD101
    from Hardware.ThorlabsMotionControl.tests.test_kim101 import KIM101TestSuite as _KIM101
    from Hardware.ThorlabsMotionControl.tests.test_tdc001 import TDC001TestSuite as _TDC001
    
    KDC101TestSuite = _KDC101
    KBD101TestSuite = _KBD101
    KIM101TestSuite = _KIM101
    TDC001TestSuite = _TDC001
    _test_suites_loaded = True


def get_test_suites():
    """
    Get mapping of device types to their test suite classes.
    
    Returns
    -------
    Dict[str, type]
        Dictionary mapping device type strings (e.g., 'KDC101') to
        their corresponding test suite classes.
    """
    _load_test_suites()
    return {
        'KDC101': KDC101TestSuite,
        'KBD101': KBD101TestSuite,
        'KIM101': KIM101TestSuite,
        'TDC001': TDC001TestSuite,
    }


# Map device types to test suites - populated lazily
TEST_SUITES = {
    'KDC101': 'KDC101TestSuite',
    'KBD101': 'KBD101TestSuite', 
    'KIM101': 'KIM101TestSuite',
    'TDC001': 'TDC001TestSuite',
}


def print_header():
    """Print application header."""
    print()
    print("=" * 70)
    print("  THORLABS MOTION CONTROL - MASTER TEST RUNNER")
    print("=" * 70)
    print()


def discover_all_devices() -> List[Dict]:
    """
    Discover all connected Thorlabs motion control devices.
    
    Uses the device manager's simple discovery mode (without stage detection)
    to quickly enumerate all USB-connected Thorlabs controllers.
    
    Returns
    -------
    List[Dict]
        List of device dictionaries containing:
        - controller_type : str - Device type (e.g., 'KDC101', 'KIM101')
        - serial : str - Device serial number
        - stage : dict or None - Stage information if detected
    
    Notes
    -----
    Simple discovery is used instead of full discovery because stage
    detection can hang on some controllers during enumeration.
    """
    print("Scanning for connected devices...")
    # Use simple discovery (faster, no stage detection which can hang)
    devices = discover_devices()
    return devices


def print_device_table(devices: List[Dict]):
    """
    Print a formatted table of discovered devices.
    
    Parameters
    ----------
    devices : List[Dict]
        List of device dictionaries from discover_all_devices()
    """
    if not devices:
        print("  No devices found!")
        return
    
    print(f"\n  Found {len(devices)} device(s):\n")
    print("  " + "-" * 66)
    print(f"  {'#':<4} {'Type':<10} {'Serial':<12} {'Stage':<20} {'Test':<10}")
    print("  " + "-" * 66)
    
    for i, dev in enumerate(devices, 1):
        dev_type = dev.get('controller_type', 'Unknown')
        serial = dev.get('serial', 'Unknown')
        stage = dev.get('stage', {})
        stage_name = stage.get('part_number', '-') if stage else '-'
        has_test = "Yes" if dev_type in TEST_SUITES else "No"
        
        print(f"  {i:<4} {dev_type:<10} {serial:<12} {stage_name:<20} {has_test:<10}")
    
    print("  " + "-" * 66)
    print()


def run_test_for_device(device: Dict) -> Dict:
    """
    Run the appropriate test suite for a device.
    
    Automatically selects and executes the correct test suite based on
    the device's controller type. Handles test suite loading, execution,
    and result collection.
    
    Parameters
    ----------
    device : Dict
        Device dictionary containing at minimum:
        - controller_type : str - Device type (e.g., 'KDC101')
        - serial : str - Device serial number
    
    Returns
    -------
    Dict
        Test result dictionary containing:
        - device_type : str - Controller type tested
        - serial : str - Serial number of device
        - tested : bool - Whether tests were executed
        - passed : int - Number of tests passed
        - failed : int - Number of tests failed
        - error : str or None - Error message if test suite failed
    
    Examples
    --------
    >>> device = {'controller_type': 'KDC101', 'serial': '27503318'}
    >>> result = run_test_for_device(device)
    >>> print(f"Passed: {result['passed']}/{result['passed'] + result['failed']}")
    """
    dev_type = device.get('controller_type', 'Unknown')
    serial = device.get('serial', 'Unknown')
    
    result = {
        'device_type': dev_type,
        'serial': serial,
        'tested': False,
        'passed': 0,
        'failed': 0,
        'error': None
    }
    
    if dev_type not in TEST_SUITES:
        result['error'] = f"No test suite available for {dev_type}"
        return result
    
    # Get test suite class from lazy-loaded suites
    suites = get_test_suites()
    TestSuiteClass = suites.get(dev_type)
    
    if not TestSuiteClass:
        result['error'] = f"Test suite for {dev_type} not loaded"
        return result
    
    try:
        # Create suite with specific serial number
        suite = TestSuiteClass(serial_number=int(serial))
        
        # Run tests
        suite.run_all_tests()
        
        result['tested'] = True
        result['passed'] = suite.passed
        result['failed'] = suite.failed
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def run_tests_on_all_devices(devices: List[Dict], type_filter: Optional[str] = None) -> List[Dict]:
    """
    Run tests on all devices, optionally filtered by type.
    
    Iterates through all testable devices and executes their respective
    test suites. Provides progress output and handles pauses between
    device tests to ensure proper USB communication reset.
    
    Parameters
    ----------
    devices : List[Dict]
        List of device dictionaries from discover_all_devices()
    type_filter : Optional[str], default=None
        If provided, only test devices whose type contains this string
        (case-insensitive). E.g., 'KIM' matches 'KIM101'.
    
    Returns
    -------
    List[Dict]
        List of result dictionaries from run_test_for_device()
    """
    results = []
    
    # Filter devices if type specified
    if type_filter:
        devices = [d for d in devices if type_filter.upper() in d.get('controller_type', '').upper()]
    
    # Filter to only testable devices
    testable = [d for d in devices if d.get('controller_type') in TEST_SUITES]
    
    if not testable:
        print("  No testable devices found!")
        return results
    
    print(f"\n  Running tests on {len(testable)} device(s)...\n")
    
    for i, device in enumerate(testable, 1):
        dev_type = device.get('controller_type')
        serial = device.get('serial')
        
        print("\n" + "#" * 70)
        print(f"# TESTING DEVICE {i}/{len(testable)}: {dev_type} - {serial}")
        print("#" * 70)
        
        result = run_test_for_device(device)
        results.append(result)
        
        # Brief pause between devices
        if i < len(testable):
            print("\n  Waiting before next device...")
            time.sleep(1)
    
    return results


def print_final_summary(results: List[Dict]):
    """
    Print final summary of all test results.
    
    Displays a formatted table of per-device results and aggregate
    statistics including total tests, pass/fail counts, and overall status.
    
    Parameters
    ----------
    results : List[Dict]
        List of result dictionaries from run_tests_on_all_devices()
    """
    print("\n" + "=" * 70)
    print("  FINAL TEST SUMMARY")
    print("=" * 70)
    
    total_passed = 0
    total_failed = 0
    devices_passed = 0
    devices_failed = 0
    
    print(f"\n  {'Device':<10} {'Serial':<12} {'Tests':<10} {'Passed':<10} {'Failed':<10} {'Status':<10}")
    print("  " + "-" * 62)
    
    for r in results:
        dev_type = r['device_type']
        serial = r['serial']
        
        if r['error']:
            status = "ERROR"
            tests = "-"
            passed = "-"
            failed = "-"
            devices_failed += 1
        elif r['tested']:
            total = r['passed'] + r['failed']
            tests = str(total)
            passed = str(r['passed'])
            failed = str(r['failed'])
            total_passed += r['passed']
            total_failed += r['failed']
            
            if r['failed'] == 0:
                status = "PASS"
                devices_passed += 1
            else:
                status = "FAIL"
                devices_failed += 1
        else:
            status = "SKIP"
            tests = "-"
            passed = "-"
            failed = "-"
        
        print(f"  {dev_type:<10} {serial:<12} {tests:<10} {passed:<10} {failed:<10} {status:<10}")
    
    print("  " + "-" * 62)
    print(f"\n  Total Devices: {len(results)}")
    print(f"  Devices Passed: {devices_passed}")
    print(f"  Devices Failed: {devices_failed}")
    print(f"\n  Total Tests: {total_passed + total_failed}")
    print(f"  Tests Passed: {total_passed}")
    print(f"  Tests Failed: {total_failed}")
    
    print("\n" + "=" * 70)
    if devices_failed == 0 and total_failed == 0:
        print("  *** ALL DEVICES PASSED ALL TESTS ***")
    else:
        print(f"  *** {devices_failed} DEVICE(S) HAD FAILURES ***")
    print("=" * 70)
    print()


def interactive_selection(devices: List[Dict]) -> List[Dict]:
    """
    Let user interactively select which devices to test.
    
    Prompts the user to enter comma-separated device numbers or 'all'
    to select devices for testing.
    
    Parameters
    ----------
    devices : List[Dict]
        List of device dictionaries from discover_all_devices()
    
    Returns
    -------
    List[Dict]
        Subset of devices selected by the user, or empty list on invalid input
    """
    print("\n  Select devices to test (comma-separated numbers, or 'all'):")
    print("  Example: 1,3 or all\n")
    
    selection = input("  Your selection: ").strip().lower()
    
    if selection == 'all':
        return devices
    
    try:
        indices = [int(x.strip()) - 1 for x in selection.split(',')]
        selected = [devices[i] for i in indices if 0 <= i < len(devices)]
        return selected
    except (ValueError, IndexError):
        print("  Invalid selection!")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Thorlabs Motion Control - Master Test Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all_tests.py              Test all connected devices
  python run_all_tests.py --list       List devices without testing
  python run_all_tests.py --select     Interactive device selection
  python run_all_tests.py --type KIM   Test only KIM101 devices
  python run_all_tests.py --type KDC   Test only KDC101 devices
  python run_all_tests.py --type KBD   Test only KBD101 devices
        """
    )
    
    parser.add_argument('--list', '-l', action='store_true',
                       help='List connected devices without testing')
    parser.add_argument('--select', '-s', action='store_true',
                       help='Interactive device selection')
    parser.add_argument('--type', '-t', type=str, default=None,
                       help='Filter by device type (e.g., KIM, KDC, KBD)')
    
    args = parser.parse_args()
    
    print_header()
    
    # Discover devices
    devices = discover_all_devices()
    print_device_table(devices)
    
    if not devices:
        print("  No devices connected. Please check connections.")
        return 1
    
    # List only mode
    if args.list:
        return 0
    
    # Interactive selection
    if args.select:
        devices = interactive_selection(devices)
        if not devices:
            print("  No devices selected.")
            return 1
        print_device_table(devices)
    
    # Confirm before testing
    testable = [d for d in devices if d.get('controller_type') in TEST_SUITES]
    if args.type:
        testable = [d for d in testable if args.type.upper() in d.get('controller_type', '').upper()]
    
    if not testable:
        print("  No testable devices found with current filter.")
        return 1
    
    print(f"  Ready to test {len(testable)} device(s).")
    print("  Note: Tests include homing and movement operations.")
    confirm = input("\n  Proceed with testing? [Y/n]: ").strip().lower()
    
    if confirm and confirm != 'y':
        print("  Testing cancelled.")
        return 0
    
    # Run tests
    results = run_tests_on_all_devices(devices, args.type)
    
    # Print summary
    print_final_summary(results)
    
    # Return exit code based on results
    any_failed = any(r['failed'] > 0 or r['error'] for r in results)
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
