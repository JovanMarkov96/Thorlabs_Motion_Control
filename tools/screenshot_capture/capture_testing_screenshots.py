#!/usr/bin/env python3
"""
Capture testing screenshots for all 4 devices.

This script:
1. Launches the GUI
2. Discovers and connects to all devices
3. Runs the full test suite on each device
4. Waits for tests to complete
5. Captures the testing tab with actual results for each device
6. Also captures KIM101 config dialog with dropdown properly expanded

Usage:
    python capture_testing_screenshots.py
"""

import sys
import time
from pathlib import Path

# Ensure proper imports
script_dir = Path(__file__).parent.resolve()
qua_dir = script_dir.parent.parent
if str(qua_dir) not in sys.path:
    sys.path.insert(0, str(qua_dir))

from PyQt5.QtWidgets import (
    QApplication, QMessageBox, QPushButton, QMenu, QComboBox
)
from PyQt5.QtCore import QTimer, Qt, QPoint
from PyQt5.QtGui import QScreen

from Hardware.ThorlabsMotionControl.gui import ThorlabsMotionControlGUI, ConfigDialog


def ensure_screenshot_dir():
    """Create screenshots directory if it doesn't exist."""
    screenshot_dir = script_dir / "docs" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    return screenshot_dir


def capture_widget(widget, name, output_dir):
    """Capture a widget to a PNG file."""
    pixmap = widget.grab()
    filepath = output_dir / f"{name}.png"
    pixmap.save(str(filepath), "PNG")
    print(f"  ✓ Captured: {filepath.name}")
    return filepath


def capture_screen_region(rect, name, output_dir):
    """Capture a region of the screen."""
    screen = QApplication.primaryScreen()
    pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
    filepath = output_dir / f"{name}.png"
    pixmap.save(str(filepath), "PNG")
    print(f"  ✓ Captured: {filepath.name}")
    return filepath


def main():
    """Main function to capture testing screenshots."""
    
    print("="*70)
    print("COMPREHENSIVE TESTING SCREENSHOT CAPTURE")
    print("="*70)
    print("\nThis script will:")
    print("  1. Launch the GUI and discover devices")
    print("  2. Connect to all 4 devices")
    print("  3. Run FULL test suites on each device")
    print("  4. Capture testing tabs with actual results")
    print("  5. Capture KIM101 config dialog with dropdown")
    print("\n⚠️  This may take several minutes as tests run on real hardware.")
    print("="*70 + "\n")
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    screenshot_dir = ensure_screenshot_dir()
    print(f"Output directory: {screenshot_dir}\n")
    
    gui = ThorlabsMotionControlGUI()
    gui.resize(1400, 900)
    gui.show()
    
    screenshots_captured = []
    
    def run_capture_sequence():
        """Main capture sequence - runs after GUI is ready."""
        nonlocal screenshots_captured
        
        try:
            # ============================================
            # PHASE 1: Device Discovery
            # ============================================
            print("PHASE 1: Discovering devices...")
            gui._discover_devices()
            QApplication.processEvents()
            time.sleep(1.0)
            
            device_count = len(gui.devices)
            print(f"  Found {device_count} devices")
            
            if device_count == 0:
                print("\n❌ No devices found! Cannot capture testing screenshots.")
                QMessageBox.warning(gui, "No Devices", "No Thorlabs devices found.")
                QTimer.singleShot(1000, app.quit)
                return
            
            # List devices
            for serial, device in gui.devices.items():
                print(f"    • {device.device_type} ({serial})")
            
            # ============================================
            # PHASE 2: Connect to All Devices
            # ============================================
            print("\nPHASE 2: Connecting to all devices...")
            gui._connect_all()
            QApplication.processEvents()
            time.sleep(2.0)  # Give time for connections
            
            connected_count = sum(1 for d in gui.devices.values() if d.controller is not None)
            print(f"  Connected to {connected_count}/{device_count} devices")
            
            # ============================================
            # PHASE 3: Run Tests on Each Device
            # ============================================
            print("\nPHASE 3: Running tests on each device...")
            
            device_types_captured = set()
            
            for tab_idx in range(gui.device_tabs.count()):
                tab_text = gui.device_tabs.tabText(tab_idx)
                device_widget = gui.device_tabs.widget(tab_idx)
                
                print(f"\n  [{tab_idx+1}/{gui.device_tabs.count()}] {tab_text}")
                
                # Switch to this device's tab
                gui.device_tabs.setCurrentIndex(tab_idx)
                QApplication.processEvents()
                time.sleep(0.3)
                
                # Switch to Testing sub-tab
                if hasattr(device_widget, 'tabs'):
                    for j in range(device_widget.tabs.count()):
                        if device_widget.tabs.tabText(j).lower() == "testing":
                            device_widget.tabs.setCurrentIndex(j)
                            break
                    QApplication.processEvents()
                    time.sleep(0.2)
                
                # Find and click "Run All Tests" button
                run_all_btn = None
                for btn in device_widget.findChildren(QPushButton):
                    btn_text = btn.text().lower()
                    if "run all" in btn_text or "all tests" in btn_text:
                        run_all_btn = btn
                        break
                
                # If no "Run All", try "Quick Test" 
                if run_all_btn is None:
                    for btn in device_widget.findChildren(QPushButton):
                        btn_text = btn.text().lower()
                        if "quick" in btn_text or "test" in btn_text:
                            run_all_btn = btn
                            break
                
                if run_all_btn and run_all_btn.isEnabled():
                    print(f"    Running tests: '{run_all_btn.text()}'...")
                    run_all_btn.click()
                    QApplication.processEvents()
                    
                    # Wait for tests to complete
                    # Check progress bar or wait for button to be re-enabled
                    max_wait = 60  # Max 60 seconds per device
                    wait_count = 0
                    
                    while wait_count < max_wait:
                        time.sleep(0.5)
                        QApplication.processEvents()
                        
                        # Check if progress bar is at 100%
                        progress_bars = device_widget.findChildren(type(device_widget).__bases__[0])
                        
                        # Better check: see if button is enabled again
                        if run_all_btn.isEnabled():
                            # Wait a bit more for log to fully update
                            time.sleep(0.5)
                            QApplication.processEvents()
                            break
                        
                        wait_count += 0.5
                        
                        if wait_count % 5 == 0:
                            print(f"    ... waiting ({int(wait_count)}s)")
                    
                    if wait_count >= max_wait:
                        print(f"    ⚠ Timeout waiting for tests")
                    else:
                        print(f"    ✓ Tests completed in ~{int(wait_count)}s")
                else:
                    print(f"    ⚠ No test button found or button disabled")
                
                # Ensure testing tab is visible
                if hasattr(device_widget, 'tabs'):
                    for j in range(device_widget.tabs.count()):
                        if device_widget.tabs.tabText(j).lower() == "testing":
                            device_widget.tabs.setCurrentIndex(j)
                            break
                QApplication.processEvents()
                time.sleep(0.3)
                
                # Capture the main window showing this device's testing tab
                # Extract device type from tab name (e.g., "KDC101 (27503318)" -> "KDC101")
                device_type = tab_text.split()[0] if tab_text else f"Device{tab_idx+1}"
                serial = tab_text.split("(")[1].rstrip(")") if "(" in tab_text else ""
                
                # Capture full window
                filename = f"testing_{device_type}_{serial}_full"
                f = capture_widget(gui, filename, screenshot_dir)
                screenshots_captured.append((f"{device_type} Testing (Full Window)", f))
                
                # Capture just the device widget
                filename = f"testing_{device_type}_{serial}_detail"
                f = capture_widget(device_widget, filename, screenshot_dir)
                screenshots_captured.append((f"{device_type} Testing (Detail)", f))
                
                device_types_captured.add(device_type)
            
            # ============================================
            # PHASE 4: KIM101 Config Dialog with Dropdown
            # ============================================
            print("\n\nPHASE 4: Capturing KIM101 config dialog with dropdown...")
            
            kim101_device = None
            for serial, device in gui.devices.items():
                # Check if it's KIM101 - the device_type might be enum or string
                dtype = str(device.device_type)
                if "INERTIAL" in dtype or "KIM" in dtype or serial == "97101306":
                    kim101_device = device
                    break
            
            if kim101_device:
                # Create config dialog
                dialog = ConfigDialog(kim101_device, channel=1, parent=gui)
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                QApplication.processEvents()
                time.sleep(0.3)
                
                # Check for channel combo
                if hasattr(dialog, 'channel_combo') and dialog.channel_combo is not None:
                    combo = dialog.channel_combo
                    
                    # Capture with channel 1
                    f = capture_widget(dialog, "config_kim101_channel1", screenshot_dir)
                    screenshots_captured.append(("KIM101 Config - Channel 1", f))
                    
                    # Show dropdown popup
                    combo.showPopup()
                    QApplication.processEvents()
                    time.sleep(0.3)
                    
                    # Get the popup widget (it's a QListView in a QFrame)
                    popup = combo.view()
                    if popup and popup.isVisible():
                        # The popup is a separate window, need to capture screen region
                        popup_parent = popup.window()
                        if popup_parent:
                            # Capture the entire dialog + popup together via screen grab
                            # Get dialog geometry
                            dialog_rect = dialog.frameGeometry()
                            popup_rect = popup_parent.frameGeometry()
                            
                            # Calculate combined region
                            combined_x = min(dialog_rect.x(), popup_rect.x())
                            combined_y = min(dialog_rect.y(), popup_rect.y())
                            combined_right = max(dialog_rect.right(), popup_rect.right())
                            combined_bottom = max(dialog_rect.bottom(), popup_rect.bottom())
                            
                            from PyQt5.QtCore import QRect
                            combined_rect = QRect(
                                combined_x, combined_y,
                                combined_right - combined_x + 1,
                                combined_bottom - combined_y + 1
                            )
                            
                            # Capture screen region
                            screen = QApplication.primaryScreen()
                            pixmap = screen.grabWindow(
                                0, combined_rect.x(), combined_rect.y(),
                                combined_rect.width(), combined_rect.height()
                            )
                            filepath = screenshot_dir / "config_kim101_dropdown_open.png"
                            pixmap.save(str(filepath), "PNG")
                            print(f"  ✓ Captured: {filepath.name}")
                            screenshots_captured.append(("KIM101 Config - Dropdown Open", filepath))
                    
                    combo.hidePopup()
                    QApplication.processEvents()
                    
                    # Change to channel 4 to show all channels work
                    combo.setCurrentIndex(3)  # Channel 4
                    QApplication.processEvents()
                    time.sleep(0.2)
                    
                    f = capture_widget(dialog, "config_kim101_channel4", screenshot_dir)
                    screenshots_captured.append(("KIM101 Config - Channel 4", f))
                else:
                    print("  ⚠ KIM101 config dialog has no channel_combo")
                    f = capture_widget(dialog, "config_kim101", screenshot_dir)
                    screenshots_captured.append(("KIM101 Config Dialog", f))
                
                dialog.close()
            else:
                print("  ⚠ KIM101 not found - skipping config dialog capture")
            
            # ============================================
            # PHASE 5: Summary
            # ============================================
            print("\n" + "="*70)
            print(f"CAPTURE COMPLETE: {len(screenshots_captured)} screenshots")
            print("="*70)
            
            print("\nCaptured files:")
            for desc, filepath in screenshots_captured:
                print(f"  • {filepath.name}: {desc}")
            
            print(f"\nSaved to: {screenshot_dir}")
            
            # Show completion dialog
            msg = QMessageBox(gui)
            msg.setWindowTitle("Screenshot Capture Complete")
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Captured {len(screenshots_captured)} screenshots successfully!")
            msg.setDetailedText("\n".join(f"• {f.name}" for _, f in screenshots_captured))
            msg.exec_()
            
        except Exception as e:
            print(f"\n❌ Error during capture: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(gui, "Error", f"Capture failed:\n{e}")
        
        finally:
            QTimer.singleShot(1000, app.quit)
    
    # Start capture after GUI is fully loaded
    QTimer.singleShot(1500, run_capture_sequence)
    
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
