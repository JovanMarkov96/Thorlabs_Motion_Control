# Screenshot Capture Tools

Automated scripts for capturing GUI screenshots for documentation.

## Scripts

### `capture_screenshots.py`
Full automated capture session - discovers devices, opens GUI, captures all major views.

```bash
cd Hardware/ThorlabsMotionControl/tools/screenshot_capture
python capture_screenshots.py
```

### `capture_testing_screenshots.py`
Runs actual tests on all 4 connected devices and captures the testing tabs with real test results.

```bash
python capture_testing_screenshots.py
```

**Note:** This takes several minutes as it runs the full test suite on each device.

### `capture_kim101_config.py`
Captures the KIM101 configuration dialog with the channel dropdown properly expanded.

```bash
python capture_kim101_config.py
```

## Output

All screenshots are saved to:
```
ThorlabsMotionControl/docs/screenshots/
```

## Requirements

- PyQt5
- Connected Thorlabs devices (KDC101, KBD101, TDC001, KIM101)
- GUI must be functional

## Usage from Main Directory

You can also run these from the main Qua directory:

```bash
cd "D:\...\Qua"
python -m Hardware.ThorlabsMotionControl.tools.screenshot_capture.capture_screenshots
```
