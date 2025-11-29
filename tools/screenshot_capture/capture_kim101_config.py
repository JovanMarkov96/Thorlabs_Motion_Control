#!/usr/bin/env python3
"""
Capture KIM101 config dialog with channel dropdown properly shown.
"""

import sys
import time
from pathlib import Path

script_dir = Path(__file__).parent.resolve()
qua_dir = script_dir.parent.parent
if str(qua_dir) not in sys.path:
    sys.path.insert(0, str(qua_dir))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, QRect

from Hardware.ThorlabsMotionControl.gui import ThorlabsMotionControlGUI, ConfigDialog


def main():
    print("="*60)
    print("KIM101 Config Dialog Screenshot Capture")
    print("="*60)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    screenshot_dir = script_dir / "docs" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {screenshot_dir}\n")
    
    gui = ThorlabsMotionControlGUI()
    gui.resize(1200, 800)
    gui.show()
    
    screenshots = []
    
    def capture():
        nonlocal screenshots
        
        try:
            # Discover devices
            print("Discovering devices...")
            gui._discover_devices()
            QApplication.processEvents()
            time.sleep(1.0)
            
            # Find KIM101
            kim101_device = None
            for serial, device in gui.devices.items():
                dtype = str(device.device_type)
                print(f"  Device {serial}: {dtype}")
                if "INERTIAL" in dtype or "KIM" in dtype:
                    kim101_device = device
                    print(f"  -> Found KIM101!")
                    break
            
            if not kim101_device:
                print("\n❌ KIM101 not found!")
                QTimer.singleShot(1000, app.quit)
                return
            
            print(f"\nOpening config dialog for KIM101 ({kim101_device.serial})...")
            
            # Create dialog
            dialog = ConfigDialog(kim101_device, channel=1, parent=gui)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            QApplication.processEvents()
            time.sleep(0.5)
            
            # Check for channel combo
            if hasattr(dialog, 'channel_combo') and dialog.channel_combo is not None:
                combo = dialog.channel_combo
                print(f"Channel combo found with {combo.count()} items")
                
                # Capture with channel 1
                pixmap = dialog.grab()
                path = screenshot_dir / "config_kim101_ch1.png"
                pixmap.save(str(path), "PNG")
                print(f"  ✓ {path.name}")
                screenshots.append(path)
                
                # Show dropdown popup and capture via screen grab
                combo.showPopup()
                QApplication.processEvents()
                time.sleep(0.4)
                
                # Capture the screen region containing dialog + dropdown
                screen = QApplication.primaryScreen()
                
                # Get dialog position
                dialog_rect = dialog.frameGeometry()
                
                # The popup appears below the combo box - estimate its position
                combo_global = combo.mapToGlobal(combo.rect().bottomLeft())
                popup_height = combo.count() * 25 + 10  # Estimate popup height
                
                # Combined capture region
                capture_x = dialog_rect.x()
                capture_y = dialog_rect.y()
                capture_width = dialog_rect.width()
                capture_height = dialog_rect.height() + popup_height + 20
                
                pixmap = screen.grabWindow(0, capture_x, capture_y, capture_width, capture_height)
                path = screenshot_dir / "config_kim101_dropdown_expanded.png"
                pixmap.save(str(path), "PNG")
                print(f"  ✓ {path.name}")
                screenshots.append(path)
                
                combo.hidePopup()
                QApplication.processEvents()
                
                # Switch to channel 2
                combo.setCurrentIndex(1)
                QApplication.processEvents()
                time.sleep(0.2)
                
                pixmap = dialog.grab()
                path = screenshot_dir / "config_kim101_ch2.png"
                pixmap.save(str(path), "PNG")
                print(f"  ✓ {path.name}")
                screenshots.append(path)
                
                # Switch to channel 4
                combo.setCurrentIndex(3)
                QApplication.processEvents()
                time.sleep(0.2)
                
                pixmap = dialog.grab()
                path = screenshot_dir / "config_kim101_ch4.png"
                pixmap.save(str(path), "PNG")
                print(f"  ✓ {path.name}")
                screenshots.append(path)
                
            else:
                print("  ⚠ No channel_combo found in dialog")
                pixmap = dialog.grab()
                path = screenshot_dir / "config_kim101.png"
                pixmap.save(str(path), "PNG")
                print(f"  ✓ {path.name}")
                screenshots.append(path)
            
            dialog.close()
            
            print(f"\n✓ Captured {len(screenshots)} screenshots")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            QTimer.singleShot(1000, app.quit)
    
    QTimer.singleShot(1000, capture)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
