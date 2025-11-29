#!/usr/bin/env python
"""
GUI Screenshot Capture Utility
==============================

Automatically captures screenshots of the ThorlabsMotionControl GUI
for documentation purposes.

Usage
-----
Run from command line::

    python -m Hardware.ThorlabsMotionControl.capture_screenshots
    
Or::

    python capture_screenshots.py

This will:
1. Launch the GUI
2. Automatically navigate through different views
3. Capture screenshots to the docs/screenshots/ folder
4. Generate a manifest of captured images

Requirements
------------
- PyQt5
- pillow (for image processing, optional)

Notes
-----
Screenshots are saved as PNG files with descriptive names.
The script simulates user interactions to capture different states.

Author
------
Weizmann Institute Ion Trap Lab (Lab185)
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Ensure proper import path
script_dir = Path(__file__).parent
if str(script_dir.parent) not in sys.path:
    sys.path.insert(0, str(script_dir.parent.parent))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QScreen


def ensure_screenshot_dir():
    """Create screenshots directory if it doesn't exist."""
    screenshot_dir = script_dir / "docs" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    return screenshot_dir


def capture_widget(widget, filename: str, screenshot_dir: Path) -> Path:
    """
    Capture a screenshot of a widget.
    
    Args:
        widget: QWidget to capture
        filename: Output filename (without extension)
        screenshot_dir: Directory to save screenshots
        
    Returns:
        Path to saved screenshot
    """
    # Ensure widget is visible and rendered
    widget.repaint()
    QApplication.processEvents()
    
    # Capture using grab()
    pixmap = widget.grab()
    
    # Save
    filepath = screenshot_dir / f"{filename}.png"
    pixmap.save(str(filepath), "PNG")
    print(f"  ✓ Captured: {filepath.name}")
    
    return filepath


def run_screenshot_session():
    """
    Run an automated screenshot capture session.
    
    This function launches the GUI and captures screenshots of:
    1. Main window (initial state)
    2. Device discovery
    3. Device tabs (Controls and Testing)
    4. Configuration dialog
    5. Different device types (KDC101, KIM101, etc.)
    """
    from Hardware.ThorlabsMotionControl.gui import ThorlabsMotionControlGUI
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    screenshot_dir = ensure_screenshot_dir()
    captured_files = []
    
    print("\n" + "="*60)
    print("ThorlabsMotionControl GUI Screenshot Capture")
    print("="*60)
    print(f"\nOutput directory: {screenshot_dir}")
    print("\nStarting capture session...\n")
    
    # Create main window
    gui = ThorlabsMotionControlGUI()
    gui.resize(1200, 800)
    gui.show()
    
    # Wait for window to fully render
    QApplication.processEvents()
    time.sleep(0.5)
    
    # Screenshot sequence
    screenshots = []
    
    def capture_sequence():
        nonlocal screenshots
        
        try:
            # 1. Main window - initial state
            print("1. Capturing main window (initial state)...")
            f = capture_widget(gui, "01_main_window_initial", screenshot_dir)
            screenshots.append(("Main Window (Initial)", f))
            
            # 2. After device discovery (if devices are connected)
            print("2. Triggering device discovery...")
            gui._discover_devices()
            QApplication.processEvents()
            time.sleep(1.0)
            
            f = capture_widget(gui, "02_main_window_with_devices", screenshot_dir)
            screenshots.append(("Main Window (Devices Discovered)", f))
            
            # 3. Capture device tree expanded
            print("3. Expanding device tree...")
            tree = gui.device_tree
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                tree.expandItem(item)
            QApplication.processEvents()
            
            f = capture_widget(gui, "03_device_tree_expanded", screenshot_dir)
            screenshots.append(("Device Tree Expanded", f))
            
            # 4. Capture each device tab
            print("4. Capturing device tabs...")
            tab_widget = gui.device_tabs
            for i in range(tab_widget.count()):
                tab_widget.setCurrentIndex(i)
                QApplication.processEvents()
                time.sleep(0.3)
                
                tab_name = tab_widget.tabText(i).replace(" ", "_").replace("/", "-")
                f = capture_widget(gui, f"04_device_tab_{i+1}_{tab_name}", screenshot_dir)
                screenshots.append((f"Device Tab: {tab_widget.tabText(i)}", f))
                
                # Try to capture Controls and Testing sub-tabs
                device_widget = tab_widget.widget(i)
                if hasattr(device_widget, 'tabs'):
                    inner_tabs = device_widget.tabs
                    for j in range(inner_tabs.count()):
                        inner_tabs.setCurrentIndex(j)
                        QApplication.processEvents()
                        time.sleep(0.2)
                        
                        inner_name = inner_tabs.tabText(j)
                        f = capture_widget(
                            gui,
                            f"04_device_tab_{i+1}_{tab_name}_{inner_name.lower()}",
                            screenshot_dir
                        )
                        screenshots.append((f"  └─ {tab_widget.tabText(i)} → {inner_name}", f))
            
            # 5. Try to open configuration dialog
            print("5. Capturing configuration dialog...")
            if gui.devices:
                # Get first device
                first_serial = list(gui.devices.keys())[0]
                first_device = gui.devices[first_serial]
                
                # Create config dialog
                from Hardware.ThorlabsMotionControl.gui import ConfigDialog
                dialog = ConfigDialog(first_device, channel=1, parent=gui)
                dialog.show()
                QApplication.processEvents()
                time.sleep(0.3)
                
                f = capture_widget(dialog, "05_config_dialog", screenshot_dir)
                screenshots.append(("Configuration Dialog", f))
                
                dialog.close()
            
            # 6. Final summary screenshot
            print("6. Final main window capture...")
            f = capture_widget(gui, "06_main_window_final", screenshot_dir)
            screenshots.append(("Main Window (Final)", f))
            
            # Generate manifest
            generate_manifest(screenshots, screenshot_dir)
            
            print("\n" + "="*60)
            print(f"Screenshot capture complete! {len(screenshots)} images saved.")
            print("="*60)
            
            # Show completion message
            QMessageBox.information(
                gui,
                "Screenshot Capture Complete",
                f"Captured {len(screenshots)} screenshots.\n\n"
                f"Saved to:\n{screenshot_dir}\n\n"
                "Check SCREENSHOT_MANIFEST.md for details."
            )
            
        except Exception as e:
            print(f"\nError during capture: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Close after a delay
            QTimer.singleShot(2000, app.quit)
    
    # Start capture sequence after GUI is ready
    QTimer.singleShot(1500, capture_sequence)
    
    # Run event loop
    sys.exit(app.exec_())


def capture_missing_screenshots():
    """
    Capture only the missing screenshots:
    1. KIM101 config dialog with channel selector
    2. Testing tab with actual test results
    3. Context menu (right-click on device)
    """
    from Hardware.ThorlabsMotionControl.gui import ThorlabsMotionControlGUI, ConfigDialog
    from PyQt5.QtWidgets import QMenu
    from PyQt5.QtCore import QPoint
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    screenshot_dir = ensure_screenshot_dir()
    screenshots = []
    
    print("\n" + "="*60)
    print("Capturing MISSING Screenshots")
    print("="*60)
    print(f"\nOutput directory: {screenshot_dir}")
    print("\nTargets:")
    print("  1. KIM101 config dialog with channel selector")
    print("  2. Testing tab with test results")
    print("  3. Context menu (right-click)")
    print("\nStarting capture...\n")
    
    # Create main window
    gui = ThorlabsMotionControlGUI()
    gui.resize(1200, 800)
    gui.show()
    
    QApplication.processEvents()
    time.sleep(0.5)
    
    def capture_sequence():
        nonlocal screenshots
        
        try:
            # Discover devices first
            print("Discovering devices...")
            gui._discover_devices()
            QApplication.processEvents()
            time.sleep(1.0)
            
            # Find KIM101 device
            kim101_device = None
            kim101_serial = None
            for serial, device in gui.devices.items():
                if device.controller_type == "KIM101":
                    kim101_device = device
                    kim101_serial = serial
                    break
            
            # ============================================
            # 1. KIM101 Config Dialog with Channel Selector
            # ============================================
            if kim101_device:
                print("\n1. Capturing KIM101 config dialog with channel selector...")
                
                # Open config dialog for KIM101
                dialog = ConfigDialog(kim101_device, channel=1, parent=gui)
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                QApplication.processEvents()
                time.sleep(0.3)
                
                # Capture with channel 1 selected
                f = capture_widget(dialog, "07_config_dialog_kim101_ch1", screenshot_dir)
                screenshots.append(("KIM101 Config Dialog (Channel 1)", f))
                
                # Change to channel 2 to show the dropdown works
                if hasattr(dialog, 'channel_combo'):
                    dialog.channel_combo.setCurrentIndex(1)  # Channel 2
                    QApplication.processEvents()
                    time.sleep(0.2)
                    
                    f = capture_widget(dialog, "08_config_dialog_kim101_ch2", screenshot_dir)
                    screenshots.append(("KIM101 Config Dialog (Channel 2)", f))
                    
                    # Show dropdown expanded
                    dialog.channel_combo.showPopup()
                    QApplication.processEvents()
                    time.sleep(0.3)
                    
                    f = capture_widget(dialog, "09_config_dialog_kim101_dropdown", screenshot_dir)
                    screenshots.append(("KIM101 Config Dialog (Channel Dropdown)", f))
                    
                    dialog.channel_combo.hidePopup()
                
                dialog.close()
                QApplication.processEvents()
            else:
                print("  ⚠ KIM101 not found - skipping config dialog capture")
            
            # ============================================
            # 2. Context Menu (Right-click on device)
            # ============================================
            print("\n2. Capturing context menu...")
            
            if gui.device_tree.topLevelItemCount() > 0:
                # Get the first device item
                first_item = gui.device_tree.topLevelItem(0)
                if first_item.childCount() > 0:
                    # Get first child (actual device)
                    device_item = first_item.child(0)
                else:
                    device_item = first_item
                
                # Select and scroll to the item
                gui.device_tree.setCurrentItem(device_item)
                gui.device_tree.scrollToItem(device_item)
                QApplication.processEvents()
                
                # Get item rect for positioning
                item_rect = gui.device_tree.visualItemRect(device_item)
                menu_pos = gui.device_tree.mapToGlobal(item_rect.center())
                
                # Create the context menu manually (same as _show_context_menu)
                serial = device_item.data(0, Qt.UserRole)
                if serial and serial in gui.devices:
                    device = gui.devices[serial]
                    
                    menu = QMenu(gui)
                    menu.addAction("⚙ Configure...")
                    menu.addSeparator()
                    if device.controller:
                        menu.addAction("⏏ Disconnect")
                    else:
                        menu.addAction("🔌 Connect")
                    menu.addSeparator()
                    menu.addAction("🔦 Identify")
                    
                    # Show menu and capture
                    menu.popup(menu_pos)
                    QApplication.processEvents()
                    time.sleep(0.3)
                    
                    # Capture the menu
                    f = capture_widget(menu, "10_context_menu", screenshot_dir)
                    screenshots.append(("Device Context Menu", f))
                    
                    menu.close()
                    QApplication.processEvents()
            else:
                print("  ⚠ No devices in tree - skipping context menu capture")
            
            # ============================================
            # 3. Testing Tab with Actual Test Results
            # ============================================
            print("\n3. Capturing testing tab with results...")
            
            # Find KIM101 or first device tab
            tab_widget = gui.device_tabs
            target_tab_idx = -1
            target_device_widget = None
            
            # Prefer KIM101 for testing
            for i in range(tab_widget.count()):
                tab_text = tab_widget.tabText(i)
                if "KIM101" in tab_text:
                    target_tab_idx = i
                    target_device_widget = tab_widget.widget(i)
                    break
            
            # Fallback to first tab
            if target_tab_idx < 0 and tab_widget.count() > 0:
                target_tab_idx = 0
                target_device_widget = tab_widget.widget(0)
            
            if target_device_widget and hasattr(target_device_widget, 'tabs'):
                # Switch to device tab
                tab_widget.setCurrentIndex(target_tab_idx)
                QApplication.processEvents()
                
                # Switch to Testing sub-tab
                inner_tabs = target_device_widget.tabs
                for j in range(inner_tabs.count()):
                    if inner_tabs.tabText(j).lower() == "testing":
                        inner_tabs.setCurrentIndex(j)
                        break
                QApplication.processEvents()
                time.sleep(0.3)
                
                # Run a quick test to populate the log
                print("  Running quick connection test...")
                
                # Find and click a test button (connection test is fastest)
                test_buttons = target_device_widget.findChildren(QPushButton)
                connection_test_btn = None
                for btn in test_buttons:
                    btn_text = btn.text().lower()
                    if "connection" in btn_text or "identify" in btn_text:
                        connection_test_btn = btn
                        break
                
                if connection_test_btn:
                    connection_test_btn.click()
                    QApplication.processEvents()
                    
                    # Wait for test to complete (with timeout)
                    for _ in range(30):  # Max 3 seconds
                        time.sleep(0.1)
                        QApplication.processEvents()
                        # Check if progress bar is done
                        if hasattr(target_device_widget, 'progress_bar'):
                            if target_device_widget.progress_bar.value() == target_device_widget.progress_bar.maximum():
                                break
                    
                    time.sleep(0.5)  # Extra time for log to update
                    QApplication.processEvents()
                
                # Capture the testing tab with results
                f = capture_widget(gui, "11_testing_with_results", screenshot_dir)
                screenshots.append(("Testing Tab with Results", f))
                
                # Also capture just the device widget
                f = capture_widget(target_device_widget, "12_testing_tab_detail", screenshot_dir)
                screenshots.append(("Testing Tab Detail", f))
            else:
                print("  ⚠ No suitable device tab found - skipping testing capture")
            
            # ============================================
            # Summary
            # ============================================
            print("\n" + "="*60)
            print(f"Missing screenshots captured: {len(screenshots)} images")
            print("="*60)
            
            for desc, filepath in screenshots:
                print(f"  ✓ {desc}: {filepath.name}")
            
            # Show completion message
            QMessageBox.information(
                gui,
                "Missing Screenshots Captured",
                f"Captured {len(screenshots)} missing screenshots.\n\n"
                f"Saved to:\n{screenshot_dir}\n\n"
                "Files:\n" + "\n".join(f"• {f.name}" for _, f in screenshots)
            )
            
        except Exception as e:
            print(f"\nError during capture: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            QTimer.singleShot(2000, app.quit)
    
    # Need to import QPushButton for test button search
    from PyQt5.QtWidgets import QPushButton
    
    # Start capture sequence after GUI is ready
    QTimer.singleShot(1500, capture_sequence)
    
    # Run event loop
    sys.exit(app.exec_())


def generate_manifest(screenshots: list, screenshot_dir: Path):
    """Generate a markdown manifest of captured screenshots."""
    
    manifest_path = screenshot_dir / "SCREENSHOT_MANIFEST.md"
    
    with open(manifest_path, 'w') as f:
        f.write("# GUI Screenshots\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Captured Images\n\n")
        f.write("| # | Description | Filename |\n")
        f.write("|---|-------------|----------|\n")
        
        for i, (desc, filepath) in enumerate(screenshots, 1):
            f.write(f"| {i} | {desc} | `{filepath.name}` |\n")
        
        f.write("\n## Usage in Documentation\n\n")
        f.write("Include screenshots in README.md using:\n\n")
        f.write("```markdown\n")
        f.write("![Description](docs/screenshots/filename.png)\n")
        f.write("```\n")
    
    print(f"\n  ✓ Manifest saved: {manifest_path.name}")


def generate_placeholder_guide():
    """
    Generate a guide for manual screenshot capture.
    
    Use this if automatic capture doesn't work or you want
    higher quality manual screenshots.
    """
    
    screenshot_dir = ensure_screenshot_dir()
    guide_path = screenshot_dir / "CAPTURE_GUIDE.md"
    
    guide_content = """# Manual Screenshot Capture Guide

If automatic screenshot capture doesn't work (e.g., no devices connected),
follow this guide to manually capture screenshots for documentation.

## Required Screenshots

### 1. Main Window - Initial State
**Filename:** `01_main_window_initial.png`
- Launch GUI: `python -m Hardware.ThorlabsMotionControl`
- Capture the window before clicking anything
- Shows: Toolbar, empty device tree, empty tabs

### 2. Main Window - Devices Discovered
**Filename:** `02_main_window_with_devices.png`
- Click "🔍 Discover Devices"
- Wait for devices to appear in tree
- Shows: Device tree with connected devices

### 3. Device Tree Expanded
**Filename:** `03_device_tree_expanded.png`
- Expand all device entries in the tree
- Shows: Device types, serial numbers, channels

### 4. Device Control Tabs
Capture each device type with both Controls and Testing tabs:

**KIM101 (Inertial Motor):**
- `04_kim101_controls.png` - Controls tab showing all 4 channels
- `04_kim101_testing.png` - Testing tab with test buttons

**KDC101 (DC Servo):**
- `04_kdc101_controls.png` - Controls tab with position, jog, move
- `04_kdc101_testing.png` - Testing tab

**KBD101 (Brushless DC):**
- `04_kbd101_controls.png`
- `04_kbd101_testing.png`

### 5. Configuration Dialog
**Filename:** `05_config_dialog.png`
- Right-click any device → "⚙ Configure..."
- Shows: Channel selection, stage dropdown, role field

### 6. KIM101 Channel Detail
**Filename:** `06_kim101_channel_controls.png`
- Select KIM101 → Controls tab
- Scroll to show one complete channel with all controls:
  - Position display + Set Zero
  - Jog controls (◀◀ ◀ steps ▶ ▶▶)
  - Move to position (Go to: [value] Go Home)
  - Drive parameters (Rate, Accel, Vmax)
  - Enable/Disable button
  - STOP button

### 7. Testing in Progress
**Filename:** `07_testing_in_progress.png`
- Click "Run All Tests" on any device
- Capture while tests are running
- Shows: Progress bar, log output, running indicator

### 8. Test Results
**Filename:** `08_test_results.png`
- Wait for tests to complete
- Shows: Pass/fail counts, detailed log

## Screenshot Tips

1. **Window Size:** Resize to ~1200x800 for consistent captures
2. **Theme:** Use default Fusion style for clarity
3. **Content:** Ensure text is readable, no cut-off elements
4. **Format:** Save as PNG for lossless quality

## Tools

**Windows:**
- Snipping Tool (Win+Shift+S)
- Print Screen + Paint
- ShareX (advanced)

**Capture Region:**
- Capture just the application window, not full desktop
- Include window title bar for context

## After Capture

1. Place all screenshots in: `docs/screenshots/`
2. Update `SCREENSHOT_MANIFEST.md` with descriptions
3. Reference in README.md using relative paths
"""
    
    with open(guide_path, 'w') as f:
        f.write(guide_content)
    
    print(f"Manual capture guide saved to: {guide_path}")
    return guide_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Capture GUI screenshots for documentation"
    )
    parser.add_argument(
        "--manual-guide",
        action="store_true",
        help="Generate manual capture guide instead of auto-capture"
    )
    parser.add_argument(
        "--missing",
        action="store_true",
        help="Capture only the missing screenshots (KIM101 config, testing, context menu)"
    )
    
    args = parser.parse_args()
    
    if args.manual_guide:
        generate_placeholder_guide()
    elif args.missing:
        capture_missing_screenshots()
    else:
        run_screenshot_session()
