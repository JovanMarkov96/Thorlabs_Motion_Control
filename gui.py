"""
Thorlabs Motion Control GUI
============================

PyQt5-based graphical interface for managing Thorlabs motion controllers.

Features
--------
- Device discovery and enumeration
- Per-channel controls with stage-aware settings
- Support for KDC101, KBD101, TDC001, KIM101, KPZ101
- Configuration dialog for device setup
- Status monitoring and position/voltage display
- **Integrated device testing with log output**

Usage
-----
Run standalone::

    python -m Hardware.ThorlabsMotionControl.gui
    
Or from Python::

    from Hardware.ThorlabsMotionControl.gui import main
    main()

Author
------
Weizmann Institute Ion Trap Lab (Lab185)
"""

from __future__ import annotations

# IMPORTANT: Initialize pythonnet (clr) BEFORE PyQt5 to avoid conflicts
import sys
from pathlib import Path

# Pre-load pythonnet if available (must happen before PyQt5 import)
_CLR_AVAILABLE = False
try:
    # Add Kinesis path first
    _kinesis_path = Path(r"C:\Program Files\Thorlabs\Kinesis")
    if _kinesis_path.exists() and str(_kinesis_path) not in sys.path:
        sys.path.insert(0, str(_kinesis_path))
    import clr
    _CLR_AVAILABLE = True
except ImportError:
    pass

import json
import time
import traceback
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from io import StringIO

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QLineEdit, QTreeWidget, QTreeWidgetItem, QTabWidget,
    QDialog, QDialogButtonBox, QFormLayout, QMessageBox, QSplitter,
    QFrame, QScrollArea, QSizePolicy, QStatusBar, QAction, QMenu,
    QToolBar, QApplication, QTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QTextCursor

from .device_manager import (
    discover_devices, load_device_config, save_device_config,
    get_compatible_stages, create_controller
)
from .stages import STAGES, get_stage_info
from .controllers import CONTROLLERS

if TYPE_CHECKING:
    from .base import MotorController, InertialController, PiezoController


class DeviceType(Enum):
    """Device categories for UI organization."""
    MOTOR = "Motor (DC Servo/Brushless)"
    INERTIAL = "Inertial Piezo (KIM101)"
    PIEZO = "Piezo Voltage (KPZ101)"


@dataclass
class DeviceInfo:
    """Information about a discovered device."""
    serial: int
    controller_type: str
    channels: int
    device_type: DeviceType
    config: Optional[Dict] = None
    controller: Optional[Any] = None  # Main controller (channel 1) or single-channel controller
    channel_controllers: Dict[int, Any] = field(default_factory=dict)  # Per-channel controllers for multi-channel devices


# =============================================================================
# Test Runner Classes
# =============================================================================

class TestWorker(QObject):
    """Worker object for running tests in a separate thread."""
    
    log_message = pyqtSignal(str, str)  # message, level (info/pass/fail/warn)
    test_started = pyqtSignal(str)  # test name
    test_finished = pyqtSignal(str, bool, str)  # test name, passed, details
    all_tests_finished = pyqtSignal(int, int)  # passed, failed
    progress = pyqtSignal(int, int)  # current, total
    
    def __init__(self, device_info: DeviceInfo, test_type: str = "full"):
        super().__init__()
        self.device_info = device_info
        self.test_type = test_type  # "full", "quick", "connectivity"
        self._stop_requested = False
    
    def stop(self):
        """Request test to stop."""
        self._stop_requested = True
    
    def run(self):
        """Run the test suite."""
        controller = self.device_info.controller
        ctrl_type = self.device_info.controller_type
        
        self.log_message.emit(
            f"Starting {self.test_type} test for {ctrl_type} ({self.device_info.serial})",
            "info"
        )
        self.log_message.emit("-" * 50, "info")
        
        passed = 0
        failed = 0
        
        # Get appropriate test methods based on device type
        if ctrl_type == "KIM101":
            tests = self._get_kim101_tests(controller)
        elif ctrl_type in ("KDC101", "TDC001"):
            tests = self._get_dc_servo_tests(controller)
        elif ctrl_type == "KBD101":
            tests = self._get_brushless_tests(controller)
        elif ctrl_type in ("KPZ101", "TPZ001"):
            tests = self._get_piezo_tests(controller)
        else:
            self.log_message.emit(f"Unknown controller type: {ctrl_type}", "warn")
            self.all_tests_finished.emit(0, 0)
            return
        
        # Filter tests based on test type
        if self.test_type == "connectivity":
            tests = [t for t in tests if t[0] in ("Identify", "Get Status", "Get Position")]
        elif self.test_type == "quick":
            tests = tests[:8]  # First 8 tests
        
        total = len(tests)
        
        for i, (name, test_func) in enumerate(tests):
            if self._stop_requested:
                self.log_message.emit("Test stopped by user", "warn")
                break
            
            self.progress.emit(i + 1, total)
            self.test_started.emit(name)
            
            try:
                result, details = test_func()
                if result:
                    passed += 1
                    self.test_finished.emit(name, True, details)
                    self.log_message.emit(f"[PASS] {name}: {details}", "pass")
                else:
                    failed += 1
                    self.test_finished.emit(name, False, details)
                    self.log_message.emit(f"[FAIL] {name}: {details}", "fail")
            except Exception as e:
                failed += 1
                error_msg = str(e)
                self.test_finished.emit(name, False, error_msg)
                self.log_message.emit(f"[FAIL] {name}: {error_msg}", "fail")
            
            # Small delay between tests
            time.sleep(0.1)
        
        self.log_message.emit("-" * 50, "info")
        self.log_message.emit(
            f"Test complete: {passed} passed, {failed} failed", 
            "pass" if failed == 0 else "fail"
        )
        self.all_tests_finished.emit(passed, failed)
    
    def _get_dc_servo_tests(self, ctrl) -> List[tuple]:
        """Get test methods for DC servo controllers (KDC101, TDC001)."""
        return [
            ("Identify", lambda: self._test_identify(ctrl)),
            ("Get Status", lambda: self._test_status(ctrl)),
            ("Get Position", lambda: self._test_position(ctrl)),
            ("Get Velocity Params", lambda: self._test_velocity_params(ctrl)),
            ("Is Homed", lambda: self._test_is_homed(ctrl)),
            ("Set Velocity", lambda: self._test_set_velocity(ctrl, 5.0)),
            ("Home", lambda: self._test_home(ctrl)),
            ("Move Absolute (5°)", lambda: self._test_move_absolute(ctrl, 5.0)),
            ("Move Relative (+2°)", lambda: self._test_move_relative(ctrl, 2.0)),
            ("Move Relative (-2°)", lambda: self._test_move_relative(ctrl, -2.0)),
            ("Stop", lambda: self._test_stop(ctrl)),
            ("Return to Zero", lambda: self._test_move_absolute(ctrl, 0.0)),
        ]
    
    def _get_brushless_tests(self, ctrl) -> List[tuple]:
        """Get test methods for brushless controllers (KBD101)."""
        return [
            ("Identify", lambda: self._test_identify(ctrl)),
            ("Get Status", lambda: self._test_status(ctrl)),
            ("Get Position", lambda: self._test_position(ctrl)),
            ("Get Velocity Params", lambda: self._test_velocity_params(ctrl)),
            ("Is Homed", lambda: self._test_is_homed(ctrl)),
            ("Set Velocity", lambda: self._test_set_velocity(ctrl, 50.0)),  # Higher for brushless
            ("Home", lambda: self._test_home(ctrl)),
            ("Move Absolute (5mm)", lambda: self._test_move_absolute(ctrl, 5.0)),
            ("Move Relative (+2mm)", lambda: self._test_move_relative(ctrl, 2.0)),
            ("Move Relative (-2mm)", lambda: self._test_move_relative(ctrl, -2.0)),
            ("Stop", lambda: self._test_stop(ctrl)),
            ("Return to Zero", lambda: self._test_move_absolute(ctrl, 0.0)),
        ]
    
    def _get_kim101_tests(self, ctrl) -> List[tuple]:
        """Get test methods for KIM101 inertial controllers."""
        tests = [
            ("Identify", lambda: self._test_identify(ctrl)),
            ("Get Status", lambda: self._test_status(ctrl)),
        ]
        
        # Add per-channel tests for channel 1 (the current channel)
        ch = ctrl.channel
        tests.extend([
            (f"Get Drive Params (Ch{ch})", lambda: self._test_kim_drive_params(ctrl)),
            (f"Set Step Rate 500Hz (Ch{ch})", lambda: self._test_kim_set_step_rate(ctrl, 500)),
            (f"Set Step Rate 1000Hz (Ch{ch})", lambda: self._test_kim_set_step_rate(ctrl, 1000)),
            (f"Jog Forward (Ch{ch})", lambda: self._test_kim_jog(ctrl, 1)),
            (f"Jog Reverse (Ch{ch})", lambda: self._test_kim_jog(ctrl, -1)),
            (f"Stop (Ch{ch})", lambda: self._test_stop(ctrl)),
        ])
        
        return tests
    
    def _get_piezo_tests(self, ctrl) -> List[tuple]:
        """Get test methods for piezo controllers (KPZ101)."""
        return [
            ("Identify", lambda: self._test_identify(ctrl)),
            ("Get Status", lambda: self._test_status(ctrl)),
            ("Get Voltage", lambda: self._test_piezo_voltage(ctrl)),
            ("Set Voltage 0V", lambda: self._test_piezo_set_voltage(ctrl, 0.0)),
            ("Set Voltage 25V", lambda: self._test_piezo_set_voltage(ctrl, 25.0)),
            ("Set Voltage 37.5V", lambda: self._test_piezo_set_voltage(ctrl, 37.5)),
            ("Set Voltage 0V", lambda: self._test_piezo_set_voltage(ctrl, 0.0)),
        ]
    
    # Test implementations
    def _test_identify(self, ctrl) -> tuple:
        ctrl.identify()
        time.sleep(0.5)
        return True, "LED blink requested"
    
    def _test_status(self, ctrl) -> tuple:
        status = ctrl.get_status()
        if status:
            details = ", ".join(f"{k}={v}" for k, v in list(status.items())[:5])
            return True, details
        return False, "No status returned"
    
    def _test_position(self, ctrl) -> tuple:
        pos = ctrl.get_position()
        return True, f"Position: {pos:.4f}"
    
    def _test_velocity_params(self, ctrl) -> tuple:
        params = ctrl.get_velocity_params()
        if params:
            return True, f"max_vel={params.get('max_velocity', '?')}, accel={params.get('acceleration', '?')}"
        return False, "No params returned"
    
    def _test_is_homed(self, ctrl) -> tuple:
        homed = ctrl.is_homed()
        return True, f"Homed: {homed}"
    
    def _test_set_velocity(self, ctrl, vel) -> tuple:
        result = ctrl.set_velocity(vel)
        return result, f"Set velocity to {vel}"
    
    def _test_home(self, ctrl) -> tuple:
        self.log_message.emit("  Homing in progress...", "info")
        result = ctrl.home(wait=True, timeout=60.0)
        return result, "Homing complete"
    
    def _test_move_absolute(self, ctrl, position) -> tuple:
        self.log_message.emit(f"  Moving to {position}...", "info")
        result = ctrl.move_absolute(position, wait=True, timeout=30.0)
        actual = ctrl.get_position()
        return result, f"Target: {position}, Actual: {actual:.4f}"
    
    def _test_move_relative(self, ctrl, distance) -> tuple:
        start_pos = ctrl.get_position()
        self.log_message.emit(f"  Moving by {distance}...", "info")
        result = ctrl.move_relative(distance, wait=True, timeout=30.0)
        end_pos = ctrl.get_position()
        actual_move = end_pos - start_pos
        return result, f"Requested: {distance}, Actual: {actual_move:.4f}"
    
    def _test_stop(self, ctrl) -> tuple:
        ctrl.stop()
        return True, "Stop command sent"
    
    def _test_kim_drive_params(self, ctrl) -> tuple:
        params = ctrl.get_drive_params()
        return True, f"rate={params.get('step_rate', '?')}, accel={params.get('step_acceleration', '?')}"
    
    def _test_kim_set_step_rate(self, ctrl, rate) -> tuple:
        result = ctrl.set_step_rate(rate)
        return result, f"Set step rate to {rate}Hz"
    
    def _test_kim_jog(self, ctrl, direction) -> tuple:
        dir_str = "forward" if direction > 0 else "reverse"
        result = ctrl.jog(direction)
        time.sleep(0.5)  # Let it move a bit
        ctrl.stop()
        return result, f"Jogged {dir_str}"
    
    def _test_piezo_voltage(self, ctrl) -> tuple:
        voltage = ctrl.get_voltage()
        return True, f"Voltage: {voltage:.2f}V"
    
    def _test_piezo_set_voltage(self, ctrl, voltage) -> tuple:
        result = ctrl.set_voltage(voltage)
        time.sleep(0.3)
        actual = ctrl.get_voltage()
        return result, f"Set: {voltage}V, Actual: {actual:.2f}V"


class TestThread(QThread):
    """Thread to run tests without blocking UI."""
    
    def __init__(self, worker: TestWorker, parent=None):
        super().__init__(parent)
        self.worker = worker
    
    def run(self):
        self.worker.run()


# =============================================================================
# Configuration Dialog
# =============================================================================

class ConfigDialog(QDialog):
    """
    Dialog for configuring a device channel's stage and metadata.
    
    This dialog allows users to:
    - Select the physical stage/actuator connected to the controller
    - Assign a descriptive role/label (e.g., "HWP_729", "Mirror_X")
    - Add optional description text
    - For multi-channel devices (KIM101), configure each channel independently
    
    Configuration is persisted to config/devices.json and used by the GUI
    to provide stage-appropriate defaults (jog steps, velocity limits, etc.).
    
    Parameters
    ----------
    device_info : DeviceInfo
        Device information dataclass containing serial, controller type, etc.
    channel : int
        Channel number to configure (1-based). For single-channel devices, always 1.
    parent : QWidget, optional
        Parent widget for dialog positioning.
    
    Attributes
    ----------
    stage_combo : QComboBox
        Dropdown for selecting compatible stage types.
    role_edit : QLineEdit
        Text field for assigning a role/label.
    description_edit : QLineEdit
        Text field for optional description.
    channel_combo : QComboBox
        Channel selector (only present for multi-channel devices).
    
    Example
    -------
    >>> dialog = ConfigDialog(device_info, channel=1, parent=main_window)
    >>> if dialog.exec_() == QDialog.Accepted:
    ...     config = dialog.get_config()
    ...     save_device_config(config)
    """
    
    def __init__(self, device_info: DeviceInfo, channel: int, parent=None):
        super().__init__(parent)
        self.device_info = device_info
        self.channel = channel
        self.config = device_info.config.copy() if device_info.config else {}
        
        self.setWindowTitle(f"Configure {device_info.controller_type} - {device_info.serial}")
        self.setMinimumWidth(400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Controller info (read-only)
        form.addRow("Serial Number:", QLabel(str(self.device_info.serial)))
        form.addRow("Controller Type:", QLabel(self.device_info.controller_type))
        
        # Channel selector (for multi-channel devices)
        if self.device_info.channels > 1:
            self.channel_combo = QComboBox()
            for ch in range(1, self.device_info.channels + 1):
                self.channel_combo.addItem(f"Channel {ch}", ch)
            self.channel_combo.setCurrentIndex(self.channel - 1)
            self.channel_combo.currentIndexChanged.connect(self._on_channel_changed)
            form.addRow("Channel:", self.channel_combo)
        else:
            form.addRow("Channel:", QLabel(str(self.channel)))
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        form.addRow(line)
        
        # Stage selection
        self.stage_combo = QComboBox()
        self.stage_combo.addItem("-- Select Stage --", None)
        
        compatible_stages = get_compatible_stages(self.device_info.controller_type)
        for stage_name in compatible_stages:
            stage_info = STAGES.get(stage_name, {})
            description = stage_info.get("description", stage_name)
            self.stage_combo.addItem(f"{stage_name} - {description}", stage_name)
        
        form.addRow("Stage Type:", self.stage_combo)
        
        # Role/Label
        self.role_edit = QLineEdit()
        self.role_edit.setPlaceholderText("e.g., HWP_729, QWP_397")
        form.addRow("Role/Label:", self.role_edit)
        
        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description")
        form.addRow("Description:", self.description_edit)
        
        layout.addLayout(form)
        
        # Stage info display
        self.stage_info_group = QGroupBox("Stage Information")
        self.stage_info_layout = QFormLayout(self.stage_info_group)
        self.stage_info_labels = {}
        for field in ["Travel", "Units", "Max Velocity", "Jog Step"]:
            label = QLabel("--")
            self.stage_info_labels[field] = label
            self.stage_info_layout.addRow(f"{field}:", label)
        layout.addWidget(self.stage_info_group)
        
        # Connect stage selection to info update
        self.stage_combo.currentIndexChanged.connect(self._update_stage_info)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Load existing config
        self._load_config()
    
    def _on_channel_changed(self, index: int):
        """Handle channel selection change."""
        self.channel = self.channel_combo.currentData()
        self._load_config()
    
    def _load_config(self):
        """Load existing configuration into fields."""
        channel_key = str(self.channel)
        channel_config = self.config.get("channels", {}).get(channel_key, {})
        
        # Stage
        stage = channel_config.get("stage", "")
        idx = self.stage_combo.findData(stage)
        if idx >= 0:
            self.stage_combo.setCurrentIndex(idx)
        
        # Role
        self.role_edit.setText(channel_config.get("role", ""))
        
        # Description
        self.description_edit.setText(channel_config.get("description", ""))
    
    def _update_stage_info(self):
        """Update stage info display when selection changes."""
        stage_name = self.stage_combo.currentData()
        
        if stage_name and stage_name in STAGES:
            stage = STAGES[stage_name]
            self.stage_info_labels["Travel"].setText(str(stage.get("travel", "--")))
            self.stage_info_labels["Units"].setText(stage.get("units", "--"))
            self.stage_info_labels["Max Velocity"].setText(
                f"{stage.get('velocity_max', '--')} {stage.get('units', '')}/s"
            )
            self.stage_info_labels["Jog Step"].setText(
                f"{stage.get('jog_step_default', '--')} {stage.get('units', '')}"
            )
        else:
            for label in self.stage_info_labels.values():
                label.setText("--")
    
    def get_config(self) -> Dict:
        """Get the configuration from dialog fields."""
        channel_key = str(self.channel)
        
        if "channels" not in self.config:
            self.config["channels"] = {}
        
        self.config["channels"][channel_key] = {
            "stage": self.stage_combo.currentData() or "",
            "role": self.role_edit.text(),
            "description": self.description_edit.text(),
        }
        
        return self.config


# =============================================================================
# Channel Control Widget
# =============================================================================

class ChannelControlWidget(QWidget):
    """
    Control widget for a single channel of a motion controller.
    
    Provides device-type-specific controls:
    
    **Motor Controllers (KDC101, KBD101, TDC001):**
    - Position display (mm or degrees)
    - Jog controls with configurable step size
    - Absolute move with target position input
    - Home button to execute homing sequence
    - Velocity adjustment
    - Stop button for emergency halt
    
    **Inertial Controllers (KIM101):**
    - Position display (steps, 32-bit signed integer)
    - Set Zero button (redefine zero reference without movement)
    - Jog controls (◀◀ ◀ [steps] ▶ ▶▶)
    - Go to position with Home button (physical move to 0)
    - Drive parameters: Rate (Hz), Acceleration, Vmax (V)
    - Enable/Disable toggle
    - Emergency STOP button
    
    **Piezo Controllers (KPZ101):**
    - Voltage display
    - Voltage set control with presets
    
    Parameters
    ----------
    device_info : DeviceInfo
        Device information dataclass with controller reference.
    channel : int
        Channel number (1-based). KIM101 has 4 channels, others have 1.
    parent : QWidget, optional
        Parent widget.
    
    Signals
    -------
    position_changed : pyqtSignal(int, float)
        Emitted when position changes. Args: (channel, new_position).
    
    Notes
    -----
    For multi-channel devices like KIM101, each channel has its own
    controller instance stored in device_info.channel_controllers[channel].
    The widget uses _get_controller() to retrieve the correct one.
    
    All buttons include detailed tooltips explaining their function,
    especially distinguishing between "Set Zero" (redefines reference)
    and "Home" (physical movement to position 0).
    """
    
    position_changed = pyqtSignal(int, float)  # channel, position
    
    def __init__(self, device_info: DeviceInfo, channel: int, parent=None):
        super().__init__(parent)
        self.device_info = device_info
        self.channel = channel
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Get channel config
        channel_config = {}
        if self.device_info.config:
            channel_config = self.device_info.config.get("channels", {}).get(
                str(self.channel), {}
            )
        
        role = channel_config.get("role", f"Channel {self.channel}")
        stage = channel_config.get("stage", "")
        is_configured = bool(stage)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel(f"<b>{role}</b>")
        header.addWidget(title)
        
        if stage:
            stage_label = QLabel(f"({stage})")
            stage_label.setStyleSheet("color: #666;")
            header.addWidget(stage_label)
        else:
            warning = QLabel("ℹ️ No stage configured")
            warning.setStyleSheet("color: #3498db; font-size: 10px;")
            warning.setToolTip(
                "Stage type not set in config.\n"
                "Right-click device in tree → Configure to set stage.\n\n"
                "Controls work with default settings.\n"
                "Configure stage for optimal velocity/jog values."
            )
            header.addWidget(warning)
        
        header.addStretch()
        
        # Identify button
        identify_btn = QPushButton("🔦")
        identify_btn.setFixedSize(24, 24)
        identify_btn.setToolTip("Identify (blink LED)")
        identify_btn.clicked.connect(self._identify)
        header.addWidget(identify_btn)
        
        layout.addLayout(header)
        
        # Different controls based on device type
        if self.device_info.device_type == DeviceType.PIEZO:
            self._setup_piezo_controls(layout, is_configured)
        elif self.device_info.device_type == DeviceType.INERTIAL:
            self._setup_inertial_controls(layout, is_configured)
        else:
            self._setup_motor_controls(layout, is_configured, stage)
    
    def _setup_motor_controls(self, layout: QVBoxLayout, is_configured: bool, stage: str):
        """Setup controls for motor controllers."""
        # Position display
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position:"))
        self.position_display = QLabel("--")
        self.position_display.setStyleSheet(
            "font-weight: bold; font-size: 14px; min-width: 80px;"
        )
        pos_layout.addWidget(self.position_display)
        
        # Units
        units = "°" if stage and STAGES.get(stage, {}).get("units") == "deg" else "mm"
        self.units_label = QLabel(units)
        pos_layout.addWidget(self.units_label)
        pos_layout.addStretch()
        layout.addLayout(pos_layout)
        
        # Jog controls
        jog_layout = QHBoxLayout()
        
        self.jog_neg_btn = QPushButton("◀")
        self.jog_neg_btn.clicked.connect(lambda: self._jog(-1))
        jog_layout.addWidget(self.jog_neg_btn)
        
        self.jog_step = QDoubleSpinBox()
        self.jog_step.setRange(0.001, 360)
        self.jog_step.setDecimals(3)
        self.jog_step.setValue(
            STAGES.get(stage, {}).get("jog_step_default", 1.0) if stage else 1.0
        )
        jog_layout.addWidget(self.jog_step)
        
        self.jog_pos_btn = QPushButton("▶")
        self.jog_pos_btn.clicked.connect(lambda: self._jog(1))
        jog_layout.addWidget(self.jog_pos_btn)
        
        layout.addLayout(jog_layout)
        
        # Move to absolute
        move_layout = QHBoxLayout()
        
        self.move_target = QDoubleSpinBox()
        self.move_target.setRange(-1000, 1000)
        self.move_target.setDecimals(3)
        move_layout.addWidget(self.move_target)
        
        move_btn = QPushButton("Move")
        move_btn.clicked.connect(self._move_absolute)
        move_layout.addWidget(move_btn)
        
        home_btn = QPushButton("Home")
        home_btn.clicked.connect(self._home)
        move_layout.addWidget(home_btn)
        
        layout.addLayout(move_layout)
    
    def _setup_inertial_controls(self, layout: QVBoxLayout, is_configured: bool):
        """Setup controls for inertial piezo controllers (KIM101)."""
        
        # Use more compact margins
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # === Position & Basic Controls (combined row) ===
        top_layout = QHBoxLayout()
        
        # Position display
        top_layout.addWidget(QLabel("Position:"))
        self.step_display = QLabel("--")
        self.step_display.setStyleSheet("font-weight: bold; font-size: 14px; min-width: 80px;")
        self.step_display.setToolTip("Current position in steps from zero reference")
        top_layout.addWidget(self.step_display)
        
        # Set Zero button (redefines zero point without moving)
        set_zero_btn = QPushButton("Set Zero")
        set_zero_btn.setFixedWidth(60)
        set_zero_btn.setToolTip(
            "Set Zero: Define current position as the new zero reference point.\n"
            "The motor does NOT move - only the position counter is reset to 0.\n"
            "Use this to establish a reference point at any physical location."
        )
        set_zero_btn.clicked.connect(self._zero_position)
        top_layout.addWidget(set_zero_btn)
        
        top_layout.addStretch()
        
        # Enable/Disable channel
        self.enable_btn = QPushButton("Enabled")
        self.enable_btn.setCheckable(True)
        self.enable_btn.setFixedWidth(80)
        self.enable_btn.setToolTip(
            "Enable/Disable Channel: Toggle the channel output.\n"
            "When disabled, the channel will not respond to movement commands.\n"
            "Green = Enabled, Gray = Disabled"
        )
        self.enable_btn.clicked.connect(self._toggle_channel_enable)
        top_layout.addWidget(self.enable_btn)
        
        # Stop button
        stop_btn = QPushButton("⏹ STOP")
        stop_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        stop_btn.setFixedWidth(70)
        stop_btn.setToolTip(
            "EMERGENCY STOP: Immediately halt all movement on this channel.\n"
            "Use this to prevent damage or if something goes wrong."
        )
        stop_btn.clicked.connect(self._stop)
        top_layout.addWidget(stop_btn)
        
        layout.addLayout(top_layout)
        
        # === Jog Controls (single row) ===
        jog_layout = QHBoxLayout()
        
        jog_label = QLabel("Jog:")
        jog_label.setToolTip("Jog: Move the motor by a specified number of steps")
        jog_layout.addWidget(jog_label)
        
        self.jog_neg_btn = QPushButton("◀◀")
        self.jog_neg_btn.setFixedWidth(35)
        self.jog_neg_btn.setToolTip("Jog backward (negative direction) by the step count shown")
        self.jog_neg_btn.clicked.connect(lambda: self._jog_inertial(-1))
        jog_layout.addWidget(self.jog_neg_btn)
        
        self.jog_neg_small_btn = QPushButton("◀")
        self.jog_neg_small_btn.setFixedWidth(30)
        self.jog_neg_small_btn.setToolTip("Jog backward (negative direction) by the step count shown")
        self.jog_neg_small_btn.clicked.connect(lambda: self._jog_inertial(-1))
        jog_layout.addWidget(self.jog_neg_small_btn)
        
        self.jog_steps_spin = QSpinBox()
        self.jog_steps_spin.setRange(1, 100000)
        self.jog_steps_spin.setValue(100)
        self.jog_steps_spin.setFixedWidth(80)
        self.jog_steps_spin.setToolTip(
            "Jog Step Size: Number of steps to move per jog button press.\n"
            "Larger values = bigger movements. Typical range: 10-1000 steps."
        )
        jog_layout.addWidget(self.jog_steps_spin)
        
        self.jog_pos_small_btn = QPushButton("▶")
        self.jog_pos_small_btn.setFixedWidth(30)
        self.jog_pos_small_btn.setToolTip("Jog forward (positive direction) by the step count shown")
        self.jog_pos_small_btn.clicked.connect(lambda: self._jog_inertial(1))
        jog_layout.addWidget(self.jog_pos_small_btn)
        
        self.jog_pos_btn = QPushButton("▶▶")
        self.jog_pos_btn.setFixedWidth(35)
        self.jog_pos_btn.setToolTip("Jog forward (positive direction) by the step count shown")
        self.jog_pos_btn.clicked.connect(lambda: self._jog_inertial(1))
        jog_layout.addWidget(self.jog_pos_btn)
        
        # Sync jog to device button
        self.sync_jog_btn = QPushButton("📤")
        self.sync_jog_btn.setFixedWidth(25)
        self.sync_jog_btn.setToolTip(
            "Save to Device: Store the current jog step size in the device's memory.\n"
            "This persists the setting even after power cycling the controller."
        )
        self.sync_jog_btn.clicked.connect(self._save_jog_steps_to_device)
        jog_layout.addWidget(self.sync_jog_btn)
        
        jog_layout.addStretch()
        
        # Move to position
        goto_label = QLabel("Go to:")
        goto_label.setToolTip("Move to an absolute position (in steps from zero reference)")
        jog_layout.addWidget(goto_label)
        self.move_target_spin = QSpinBox()
        self.move_target_spin.setRange(-2147483647, 2147483647)
        self.move_target_spin.setValue(0)
        self.move_target_spin.setFixedWidth(80)
        self.move_target_spin.setToolTip(
            "Target Position: Enter the absolute position to move to (in steps).\n"
            "Positive values = forward from zero, Negative = backward from zero."
        )
        jog_layout.addWidget(self.move_target_spin)
        
        move_btn = QPushButton("Go")
        move_btn.setFixedWidth(35)
        move_btn.setToolTip(
            "Go: Move the motor to the specified target position.\n"
            "The motor will physically travel to reach this absolute position."
        )
        move_btn.clicked.connect(self._move_to_position)
        jog_layout.addWidget(move_btn)
        
        home_btn = QPushButton("Home")
        home_btn.setFixedWidth(50)
        home_btn.setToolTip(
            "Home: PHYSICALLY MOVE the motor to position 0.\n"
            "This will move the actuator back to the zero reference point.\n"
            "⚠️ The motor WILL move! Use 'Set Zero' if you only want to reset the counter."
        )
        home_btn.clicked.connect(self._move_home)
        jog_layout.addWidget(home_btn)
        
        layout.addLayout(jog_layout)
        
        # === Drive Parameters (collapsible/compact) ===
        params_layout = QHBoxLayout()
        
        rate_label = QLabel("Rate:")
        rate_label.setToolTip("Step Rate: How fast the motor moves (steps per second)")
        params_layout.addWidget(rate_label)
        self.step_rate_spin = QSpinBox()
        self.step_rate_spin.setRange(1, 2000)
        self.step_rate_spin.setValue(500)
        self.step_rate_spin.setSuffix(" Hz")
        self.step_rate_spin.setFixedWidth(80)
        self.step_rate_spin.setToolTip(
            "Step Rate (Hz): The speed of motor movement.\n"
            "Higher values = faster movement but may reduce precision.\n"
            "Typical range: 100-1000 Hz. Changes are saved to device automatically."
        )
        self.step_rate_spin.valueChanged.connect(self._on_step_rate_changed)
        params_layout.addWidget(self.step_rate_spin)
        
        accel_label = QLabel("Accel:")
        accel_label.setToolTip("Acceleration: How quickly the motor reaches full speed")
        params_layout.addWidget(accel_label)
        self.step_accel_spin = QSpinBox()
        self.step_accel_spin.setRange(1, 100000)
        self.step_accel_spin.setValue(1000)
        self.step_accel_spin.setFixedWidth(70)
        self.step_accel_spin.setToolTip(
            "Acceleration: Rate of speed change (steps/s²).\n"
            "Higher values = faster ramp-up but may cause vibration.\n"
            "Changes are saved to device automatically."
        )
        self.step_accel_spin.valueChanged.connect(self._on_step_accel_changed)
        params_layout.addWidget(self.step_accel_spin)
        
        vmax_label = QLabel("Vmax:")
        vmax_label.setToolTip("Maximum Voltage: Peak voltage applied to the piezo")
        params_layout.addWidget(vmax_label)
        self.max_voltage_spin = QSpinBox()
        self.max_voltage_spin.setRange(85, 125)
        self.max_voltage_spin.setValue(110)
        self.max_voltage_spin.setSuffix(" V")
        self.max_voltage_spin.setFixedWidth(65)
        self.max_voltage_spin.setToolTip(
            "Maximum Voltage (V): Peak drive voltage for the piezo actuator.\n"
            "Higher voltage = stronger movement but more heat.\n"
            "Range: 85-125V. Changes are saved to device automatically."
        )
        self.max_voltage_spin.valueChanged.connect(self._on_max_voltage_changed)
        params_layout.addWidget(self.max_voltage_spin)
        
        params_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(25)
        refresh_btn.setToolTip(
            "Refresh: Read all current parameter values from the device.\n"
            "Use this to sync the GUI with the actual device settings."
        )
        refresh_btn.clicked.connect(self._refresh_params_from_device)
        params_layout.addWidget(refresh_btn)
        
        layout.addLayout(params_layout)
        
        # Flag to prevent recursive parameter updates
        self._updating_params = False
    
    def _setup_piezo_controls(self, layout: QVBoxLayout, is_configured: bool):
        """Setup controls for piezo voltage controllers."""
        # Voltage display
        volt_layout = QHBoxLayout()
        volt_layout.addWidget(QLabel("Voltage:"))
        self.voltage_display = QLabel("--")
        self.voltage_display.setStyleSheet(
            "font-weight: bold; font-size: 14px; min-width: 80px;"
        )
        volt_layout.addWidget(self.voltage_display)
        volt_layout.addWidget(QLabel("V"))
        volt_layout.addStretch()
        layout.addLayout(volt_layout)
        
        # Voltage slider/spinbox
        control_layout = QHBoxLayout()
        
        self.voltage_spin = QDoubleSpinBox()
        self.voltage_spin.setRange(0, 75)  # Default KPZ101 range
        self.voltage_spin.setDecimals(2)
        self.voltage_spin.setSuffix(" V")
        control_layout.addWidget(self.voltage_spin)
        
        set_btn = QPushButton("Set")
        set_btn.clicked.connect(self._set_voltage)
        control_layout.addWidget(set_btn)
        
        layout.addLayout(control_layout)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        for preset in [0, 25, 37.5, 50, 75]:
            btn = QPushButton(f"{preset}V")
            btn.setFixedWidth(50)
            btn.clicked.connect(lambda checked, v=preset: self._set_voltage_preset(v))
            preset_layout.addWidget(btn)
        layout.addLayout(preset_layout)
    
    def _get_controller(self):
        """Get the controller for this channel."""
        # For multi-channel devices, use the channel-specific controller
        if self.device_info.channel_controllers and self.channel in self.device_info.channel_controllers:
            return self.device_info.channel_controllers[self.channel]
        # Fall back to main controller (single-channel devices)
        return self.device_info.controller
    
    def _identify(self):
        """Blink the LED on the controller."""
        ctrl = self._get_controller()
        if ctrl:
            try:
                ctrl.identify()
            except Exception as e:
                print(f"Identify failed: {e}")
    
    def _jog(self, direction: int):
        """Jog motor in given direction."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            step = self.jog_step.value() * direction
            ctrl.move_relative(step, wait=False)
        except Exception as e:
            print(f"Jog failed: {e}")
    
    def _jog_inertial(self, direction: int):
        """Jog inertial piezo in given direction."""
        ctrl = self._get_controller()
        if not ctrl:
            print(f"No controller for channel {self.channel}")
            return
        
        try:
            # Get step count from the spinbox
            steps = self.jog_steps_spin.value() * direction
            # Use move_by for explicit step count instead of jog() 
            # which uses device-configured jog parameters
            ctrl.move_by(steps)
        except Exception as e:
            print(f"Jog steps failed on channel {self.channel}: {e}")
    
    def _move_absolute(self):
        """Move to absolute position."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            target = self.move_target.value()
            ctrl.move_absolute(target, wait=False)
        except Exception as e:
            print(f"Move failed: {e}")
    
    def _home(self):
        """Home the motor."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            ctrl.home(wait=False)
        except Exception as e:
            print(f"Home failed: {e}")
    
    def _stop(self):
        """Stop any movement."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            ctrl.stop()
        except Exception as e:
            print(f"Stop failed: {e}")
    
    def _set_step_rate(self, rate: int):
        """Set inertial piezo step rate."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            ctrl.set_step_rate(rate)
        except Exception as e:
            print(f"Set step rate failed: {e}")
    
    # =========================================================================
    # Inertial Piezo (KIM101) specific methods
    # =========================================================================
    
    def _zero_position(self):
        """Set current position as zero."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            if hasattr(ctrl, 'zero_position'):
                ctrl.zero_position()
                self.step_display.setText("0")
        except Exception as e:
            print(f"Zero position failed: {e}")
    
    def _move_to_position(self):
        """Move to absolute position (for inertial)."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            target = self.move_target_spin.value()
            if hasattr(ctrl, 'move_to'):
                ctrl.move_to(target)
        except Exception as e:
            print(f"Move to position failed: {e}")
    
    def _move_home(self):
        """Move to home/zero position."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            if hasattr(ctrl, 'move_to'):
                ctrl.move_to(0)
        except Exception as e:
            print(f"Move home failed: {e}")
    
    def _save_jog_steps_to_device(self):
        """Save current jog step size to device."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            steps = self.jog_steps_spin.value()
            if hasattr(ctrl, 'set_jog_params'):
                # Set both forward and reverse jog steps to same value
                ctrl.set_jog_params(step_fwd=steps, step_rev=steps)
                print(f"Saved jog steps ({steps}) to device channel {self.channel}")
        except Exception as e:
            print(f"Save jog steps failed: {e}")
    
    def _on_step_rate_changed(self, value: int):
        """Handle step rate spinbox change."""
        if getattr(self, '_updating_params', False):
            return
        ctrl = self._get_controller()
        if ctrl and hasattr(ctrl, 'set_step_rate'):
            try:
                ctrl.set_step_rate(value)
            except Exception as e:
                print(f"Set step rate failed: {e}")
    
    def _on_step_accel_changed(self, value: int):
        """Handle step acceleration spinbox change."""
        if getattr(self, '_updating_params', False):
            return
        ctrl = self._get_controller()
        if ctrl and hasattr(ctrl, 'set_step_acceleration'):
            try:
                ctrl.set_step_acceleration(value)
            except Exception as e:
                print(f"Set step acceleration failed: {e}")
    
    def _on_max_voltage_changed(self, value: int):
        """Handle max voltage spinbox change."""
        if getattr(self, '_updating_params', False):
            return
        ctrl = self._get_controller()
        if ctrl and hasattr(ctrl, 'set_max_voltage'):
            try:
                ctrl.set_max_voltage(value)
            except Exception as e:
                print(f"Set max voltage failed: {e}")
    
    def _toggle_channel_enable(self):
        """Toggle channel enable/disable."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            if self.enable_btn.isChecked():
                if hasattr(ctrl, 'enable_channel'):
                    ctrl.enable_channel()
                self.enable_btn.setText("Enabled ✓")
                self.enable_btn.setStyleSheet("background-color: #27ae60; color: white;")
            else:
                if hasattr(ctrl, 'disable_channel'):
                    ctrl.disable_channel()
                self.enable_btn.setText("Disabled")
                self.enable_btn.setStyleSheet("")
        except Exception as e:
            print(f"Toggle channel enable failed: {e}")
    
    def _refresh_params_from_device(self):
        """Read all parameters from device and update GUI."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        self._updating_params = True
        try:
            # Get drive parameters
            if hasattr(ctrl, 'get_drive_params'):
                drive_params = ctrl.get_drive_params()
                if drive_params.get('step_rate', 0) > 0:
                    self.step_rate_spin.setValue(drive_params['step_rate'])
                if drive_params.get('step_acceleration', 0) > 0:
                    self.step_accel_spin.setValue(drive_params['step_acceleration'])
                if drive_params.get('max_voltage', 0) > 0:
                    self.max_voltage_spin.setValue(drive_params['max_voltage'])
            
            # Get jog parameters
            if hasattr(ctrl, 'get_jog_params'):
                jog_params = ctrl.get_jog_params()
                # Use forward jog step as the displayed value
                jog_step = jog_params.get('jog_step_fwd', 0)
                if jog_step > 0:
                    self.jog_steps_spin.setValue(jog_step)
            
            # Get channel enabled status
            if hasattr(ctrl, 'is_channel_enabled'):
                enabled = ctrl.is_channel_enabled()
                self.enable_btn.setChecked(enabled)
                if enabled:
                    self.enable_btn.setText("Enabled ✓")
                    self.enable_btn.setStyleSheet("background-color: #27ae60; color: white;")
                else:
                    self.enable_btn.setText("Disabled")
                    self.enable_btn.setStyleSheet("")
            
            print(f"Refreshed parameters from device for channel {self.channel}")
        except Exception as e:
            print(f"Refresh params failed: {e}")
        finally:
            self._updating_params = False
    
    def load_params_from_device(self):
        """Load parameters from device (called after connection)."""
        if self.device_info.device_type == DeviceType.INERTIAL:
            # Delay slightly to ensure device is ready
            QTimer.singleShot(500, self._refresh_params_from_device)
    
    def _set_voltage(self):
        """Set piezo voltage."""
        ctrl = self._get_controller()
        if not ctrl:
            return
        
        try:
            voltage = self.voltage_spin.value()
            ctrl.set_voltage(voltage)
        except Exception as e:
            print(f"Set voltage failed: {e}")
    
    def _set_voltage_preset(self, voltage: float):
        """Set voltage to preset value."""
        self.voltage_spin.setValue(voltage)
        self._set_voltage()
    
    def update_display(self, status: Dict[str, Any]):
        """Update the display with current status."""
        if self.device_info.device_type == DeviceType.PIEZO:
            if "voltage" in status:
                self.voltage_display.setText(f"{status['voltage']:.2f}")
        elif self.device_info.device_type == DeviceType.INERTIAL:
            # KIM101 returns position from get_channel_status()
            position = status.get("position", status.get("step_count", 0))
            if hasattr(self, 'step_display'):
                self.step_display.setText(str(position))
            
            # Update enable button based on status (if available)
            if hasattr(self, 'enable_btn') and 'is_enabled' in status:
                enabled = status.get('is_enabled', False)
                if enabled != self.enable_btn.isChecked():
                    self.enable_btn.setChecked(enabled)
                    if enabled:
                        self.enable_btn.setText("Enabled ✓")
                        self.enable_btn.setStyleSheet("background-color: #27ae60; color: white;")
                    else:
                        self.enable_btn.setText("Disabled")
                        self.enable_btn.setStyleSheet("")
        else:
            if "position" in status:
                self.position_display.setText(f"{status['position']:.3f}")


# =============================================================================
# Device Widget (with controls and testing)
# =============================================================================

class DeviceWidget(QWidget):
    """
    Complete widget for a single device with controls and testing interface.
    
    This is the main per-device container shown in the right panel of the GUI.
    It contains two sub-tabs:
    
    **Controls Tab:**
    - Channel-specific control widgets (ChannelControlWidget instances)
    - For multi-channel devices (KIM101), shows all channels in a scrollable view
    - Connection status indicator and connect/disconnect button
    
    **Testing Tab:**
    - Device-specific test suite buttons
    - Progress bar for test execution
    - Log window with timestamped test output
    - Pass/fail summary
    
    Parameters
    ----------
    device_info : DeviceInfo
        Device information including serial, controller type, and controller instance.
    parent : QWidget, optional
        Parent widget.
    
    Signals
    -------
    connect_requested : pyqtSignal(int)
        Emitted when user clicks Connect. Arg: serial number.
    disconnect_requested : pyqtSignal(int)
        Emitted when user clicks Disconnect. Arg: serial number.
    
    Attributes
    ----------
    channel_widgets : Dict[int, ChannelControlWidget]
        Map of channel number to control widget.
    tabs : QTabWidget
        Container for Controls and Testing sub-tabs.
    connect_btn : QPushButton
        Connect/Disconnect toggle button.
    connection_indicator : QLabel
        Green/red status indicator.
    log_output : QTextEdit
        Test log display area.
    progress_bar : QProgressBar
        Test execution progress.
    
    Notes
    -----
    The widget manages a QTimer for periodic status updates when connected.
    Tests run in a background thread (TestThread) to keep UI responsive.
    """
    
    # Signals for connection management
    connect_requested = pyqtSignal(int)  # serial number
    disconnect_requested = pyqtSignal(int)  # serial number
    
    def __init__(self, device_info: DeviceInfo, parent=None):
        super().__init__(parent)
        self.device_info = device_info
        self.channel_widgets: Dict[int, ChannelControlWidget] = {}
        self.test_thread: Optional[TestThread] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Device header with connection controls
        header_layout = QHBoxLayout()
        
        title = QLabel(f"<b>{self.device_info.controller_type}</b> - {self.device_info.serial}")
        title.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(title)
        
        # Connection indicator
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: #e74c3c; font-size: 16px;")
        self.connection_indicator.setToolTip("Disconnected")
        header_layout.addWidget(self.connection_indicator)
        
        header_layout.addStretch()
        
        # Identify button
        self.identify_btn = QPushButton("🔦 Identify")
        self.identify_btn.setToolTip("Blink LED on device (must be connected)")
        self.identify_btn.clicked.connect(self._on_identify)
        self.identify_btn.setEnabled(False)  # Disabled until connected
        header_layout.addWidget(self.identify_btn)
        
        # Connect button
        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.setToolTip("Connect to this device")
        self.connect_btn.clicked.connect(self._on_connect)
        self.connect_btn.setStyleSheet("background-color: #27ae60; color: white;")
        header_layout.addWidget(self.connect_btn)
        
        # Disconnect button
        self.disconnect_btn = QPushButton("⏏ Disconnect")
        self.disconnect_btn.setToolTip("Disconnect from this device")
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.disconnect_btn.setEnabled(False)  # Disabled until connected
        header_layout.addWidget(self.disconnect_btn)
        
        layout.addLayout(header_layout)
        
        # Tab widget for Controls and Testing
        self.tabs = QTabWidget()
        
        # Controls tab - with scroll area for multi-channel devices
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        controls_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        controls_scroll.setFrameShape(QFrame.NoFrame)
        
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(10)
        
        # Channel controls
        for channel in range(1, self.device_info.channels + 1):
            # Channel header with number
            channel_header = QLabel(f"<b>Channel {channel}</b>")
            channel_header.setStyleSheet("font-size: 12px; color: #2c3e50; padding: 5px; background-color: #ecf0f1; border-radius: 3px;")
            controls_layout.addWidget(channel_header)
            
            channel_widget = ChannelControlWidget(self.device_info, channel)
            controls_layout.addWidget(channel_widget)
            self.channel_widgets[channel] = channel_widget
            
            # Separator between channels
            if channel < self.device_info.channels:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("background-color: #bdc3c7; margin: 10px 0;")
                line.setFixedHeight(2)
                controls_layout.addWidget(line)
        
        controls_layout.addStretch()
        controls_scroll.setWidget(controls_widget)
        self.tabs.addTab(controls_scroll, "Controls")
        
        # Testing tab
        test_widget = self._create_test_tab()
        self.tabs.addTab(test_widget, "Testing")
        
        layout.addWidget(self.tabs)
    
    def _create_test_tab(self) -> QWidget:
        """Create the testing tab with buttons and log."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Test buttons
        btn_layout = QHBoxLayout()
        
        self.quick_test_btn = QPushButton("Quick Test")
        self.quick_test_btn.setToolTip("Run basic connectivity tests")
        self.quick_test_btn.clicked.connect(lambda: self._start_test("quick"))
        btn_layout.addWidget(self.quick_test_btn)
        
        self.full_test_btn = QPushButton("Full Test")
        self.full_test_btn.setToolTip("Run comprehensive test suite")
        self.full_test_btn.clicked.connect(lambda: self._start_test("full"))
        btn_layout.addWidget(self.full_test_btn)
        
        self.connectivity_btn = QPushButton("Connectivity Only")
        self.connectivity_btn.setToolTip("Test connection and basic commands")
        self.connectivity_btn.clicked.connect(lambda: self._start_test("connectivity"))
        btn_layout.addWidget(self.connectivity_btn)
        
        self.stop_test_btn = QPushButton("Stop Test")
        self.stop_test_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.clicked.connect(self._stop_test)
        btn_layout.addWidget(self.stop_test_btn)
        
        layout.addLayout(btn_layout)
        
        # Progress bar
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        layout.addWidget(self.test_progress)
        
        # Test log
        log_label = QLabel("Test Log:")
        layout.addWidget(log_label)
        
        self.test_log = QTextEdit()
        self.test_log.setReadOnly(True)
        self.test_log.setFont(QFont("Consolas", 9))
        self.test_log.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        self.test_log.setMinimumHeight(200)
        layout.addWidget(self.test_log)
        
        # Clear log button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.test_log.clear)
        layout.addWidget(clear_btn)
        
        return widget
    
    def _start_test(self, test_type: str):
        """Start a test of the specified type."""
        if not self.device_info.controller:
            self._log_message("Error: Device not connected!", "fail")
            QMessageBox.warning(
                self, "Not Connected",
                "Please connect to the device first before running tests."
            )
            return
        
        # Disable test buttons
        self._set_test_buttons_enabled(False)
        self.stop_test_btn.setEnabled(True)
        self.test_progress.setVisible(True)
        self.test_progress.setValue(0)
        
        # Create worker and thread
        worker = TestWorker(self.device_info, test_type)
        worker.log_message.connect(self._log_message)
        worker.progress.connect(self._update_progress)
        worker.all_tests_finished.connect(self._on_tests_finished)
        
        self.test_thread = TestThread(worker)
        self.test_thread.finished.connect(self._on_thread_finished)
        self.test_thread.start()
    
    def _stop_test(self):
        """Stop the current test."""
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.worker.stop()
            self._log_message("Stopping test...", "warn")
    
    def _set_test_buttons_enabled(self, enabled: bool):
        """Enable or disable test buttons."""
        self.quick_test_btn.setEnabled(enabled)
        self.full_test_btn.setEnabled(enabled)
        self.connectivity_btn.setEnabled(enabled)
    
    def _log_message(self, message: str, level: str = "info"):
        """Add a message to the test log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color based on level
        colors = {
            "info": "#d4d4d4",
            "pass": "#4ec9b0",
            "fail": "#f14c4c",
            "warn": "#dcdcaa",
        }
        color = colors.get(level, "#d4d4d4")
        
        html = f'<span style="color: #888;">[{timestamp}]</span> <span style="color: {color};">{message}</span>'
        self.test_log.append(html)
        
        # Scroll to bottom
        cursor = self.test_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.test_log.setTextCursor(cursor)
    
    def _update_progress(self, current: int, total: int):
        """Update progress bar."""
        self.test_progress.setMaximum(total)
        self.test_progress.setValue(current)
    
    def _on_tests_finished(self, passed: int, failed: int):
        """Called when all tests complete."""
        pass  # Handled by _on_thread_finished
    
    def _on_thread_finished(self):
        """Called when test thread finishes."""
        self._set_test_buttons_enabled(True)
        self.stop_test_btn.setEnabled(False)
        self.test_progress.setVisible(False)
        self.test_thread = None
    
    def _on_connect(self):
        """Handle connect button click."""
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")
        QApplication.processEvents()
        self.connect_requested.emit(self.device_info.serial)
    
    def _on_disconnect(self):
        """Handle disconnect button click."""
        self.disconnect_requested.emit(self.device_info.serial)
    
    def _on_identify(self):
        """Handle identify button click - blink LED."""
        if self.device_info.controller:
            try:
                self.device_info.controller.identify()
                self._log_message("LED blink command sent", "info") if hasattr(self, 'test_log') else None
            except Exception as e:
                print(f"Identify failed: {e}")
    
    def update_connection_status(self, connected: bool):
        """Update the connection indicator and button states."""
        if connected:
            self.connection_indicator.setStyleSheet("color: #27ae60; font-size: 16px;")
            self.connection_indicator.setToolTip("Connected")
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("🔌 Connected")
            self.connect_btn.setStyleSheet("")
            self.disconnect_btn.setEnabled(True)
            self.identify_btn.setEnabled(True)
            
            # Load parameters from device for each channel widget
            for channel, widget in self.channel_widgets.items():
                if hasattr(widget, 'load_params_from_device'):
                    widget.load_params_from_device()
        else:
            self.connection_indicator.setStyleSheet("color: #e74c3c; font-size: 16px;")
            self.connection_indicator.setToolTip("Disconnected")
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("🔌 Connect")
            self.connect_btn.setStyleSheet("background-color: #27ae60; color: white;")
            self.disconnect_btn.setEnabled(False)
            self.identify_btn.setEnabled(False)
    
    def update_status(self, status: Dict[str, Any]):
        """Update status displays for the device (single-channel devices)."""
        for channel, widget in self.channel_widgets.items():
            widget.update_display(status)
    
    def update_channel_status(self, channel: int, status: Dict[str, Any]):
        """Update status for a specific channel (multi-channel devices)."""
        if channel in self.channel_widgets:
            self.channel_widgets[channel].update_display(status)
    
    def set_device_info(self, device_info: DeviceInfo):
        """Update the device info (e.g., after config change)."""
        self.device_info = device_info
        # Update channel widgets with new config
        for channel, widget in self.channel_widgets.items():
            widget.device_info = device_info


# =============================================================================
# Main GUI Window
# =============================================================================

class ThorlabsMotionControlGUI(QMainWindow):
    """
    Main application window for Thorlabs Motion Control GUI.
    
    This is the top-level window containing all GUI components:
    
    **Layout:**
    - Toolbar (top): Discover, Connect All, Disconnect All buttons + status
    - Device Tree (left panel): Hierarchical list of discovered devices
    - Device Tabs (right panel): Per-device control and testing widgets
    - Status Bar (bottom): Operation feedback messages
    
    **Features:**
    - Automatic device discovery on startup
    - USB device scanning via Kinesis/APT backends
    - Per-device connection management
    - Configuration persistence to JSON
    - Periodic status polling for connected devices
    - Context menu for device operations
    - Full menu bar with File, Devices, Help menus
    
    **Device Tree:**
    - Devices organized by controller type
    - Color-coded connection status (green=connected, gray=disconnected)
    - Right-click context menu: Configure, Connect/Disconnect, Identify
    - Click to select and show device tab
    
    **Tab Management:**
    - One tab per discovered device
    - Tabs contain DeviceWidget instances
    - Tabs persist across reconnections
    
    Attributes
    ----------
    devices : Dict[int, DeviceInfo]
        Map of serial number to DeviceInfo for all discovered devices.
    device_widgets : Dict[int, DeviceWidget]
        Map of serial number to DeviceWidget for devices with tabs.
    device_tree : QTreeWidget
        Left panel device list.
    device_tabs : QTabWidget
        Right panel tab container.
    update_timer : QTimer
        Timer for periodic status updates (when devices connected).
    
    Example
    -------
    >>> from Hardware.ThorlabsMotionControl.gui import ThorlabsMotionControlGUI
    >>> from PyQt5.QtWidgets import QApplication
    >>> app = QApplication([])
    >>> gui = ThorlabsMotionControlGUI()
    >>> gui.show()
    >>> app.exec_()
    """
    
    def __init__(self):
        super().__init__()
        self.devices: Dict[int, DeviceInfo] = {}
        self.device_widgets: Dict[int, DeviceWidget] = {}
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_all_status)
        
        self._setup_ui()
        self._setup_menu()
        
        # Auto-discover on startup
        QTimer.singleShot(500, self._discover_devices)
    
    def _setup_ui(self):
        self.setWindowTitle("Thorlabs Motion Control")
        self.setMinimumSize(1000, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Toolbar (fixed height, does not stretch)
        toolbar = QHBoxLayout()
        
        discover_btn = QPushButton("🔍 Discover Devices")
        discover_btn.clicked.connect(self._discover_devices)
        toolbar.addWidget(discover_btn)
        
        connect_all_btn = QPushButton("🔌 Connect All")
        connect_all_btn.clicked.connect(self._connect_all)
        toolbar.addWidget(connect_all_btn)
        
        disconnect_all_btn = QPushButton("⏏ Disconnect All")
        disconnect_all_btn.clicked.connect(self._disconnect_all)
        toolbar.addWidget(disconnect_all_btn)
        
        toolbar.addStretch()
        
        self.status_label = QLabel("Ready")
        toolbar.addWidget(self.status_label)
        
        # Add toolbar with stretch=0 (don't expand vertically)
        layout.addLayout(toolbar, 0)
        
        # Splitter for device list and controls (stretch=1, takes all remaining space)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Device tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["Devices"])
        self.device_tree.setMinimumWidth(200)
        self.device_tree.itemClicked.connect(self._on_device_selected)
        self.device_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_tree.customContextMenuRequested.connect(self._show_context_menu)
        left_layout.addWidget(self.device_tree)
        
        splitter.addWidget(left_panel)
        
        # Right: Tab widget for devices
        self.device_tabs = QTabWidget()
        self.device_tabs.setTabsClosable(False)
        splitter.addWidget(self.device_tabs)
        
        splitter.setSizes([250, 750])
        # Add splitter with stretch=1 (expand to fill all available vertical space)
        layout.addWidget(splitter, 1)
        
        # Status bar
        self.statusBar().showMessage("Ready - Click 'Discover Devices' to scan")
    
    def _setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        save_action = QAction("&Save Configuration", self)
        save_action.triggered.connect(self._save_all_config)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Devices menu
        devices_menu = menubar.addMenu("&Devices")
        
        discover_action = QAction("&Discover", self)
        discover_action.triggered.connect(self._discover_devices)
        devices_menu.addAction(discover_action)
        
        connect_action = QAction("Connect &All", self)
        connect_action.triggered.connect(self._connect_all)
        devices_menu.addAction(connect_action)
        
        disconnect_action = QAction("&Disconnect All", self)
        disconnect_action.triggered.connect(self._disconnect_all)
        devices_menu.addAction(disconnect_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _discover_devices(self):
        """Discover connected Thorlabs devices."""
        self.status_label.setText("Discovering...")
        self.statusBar().showMessage("Scanning for Thorlabs devices...")
        QApplication.processEvents()
        
        try:
            devices_list = discover_devices()
            discovered = {}
            for dev in devices_list:
                if isinstance(dev, dict) and "serial" in dev and "controller_type" in dev:
                    # Convert serial to int if it's a string
                    serial = dev["serial"]
                    if isinstance(serial, str):
                        serial = int(serial)
                    discovered[serial] = dev["controller_type"]
            self._on_devices_found(discovered)
        except Exception as e:
            print(f"Discovery failed: {e}")
            traceback.print_exc()
            self._on_devices_found({})
        finally:
            self.status_label.setText("Ready")
    
    def _on_devices_found(self, discovered: Dict[int, str]):
        """Handle discovered devices."""
        # Load existing config
        full_config = load_device_config()
        controllers_config = full_config.get("controllers", {})
        
        # Update device list
        self.devices.clear()
        
        for serial, controller_type in discovered.items():
            ctrl_info = CONTROLLERS.get(controller_type, {})
            
            # Determine device type
            if controller_type == "KIM101":
                device_type = DeviceType.INERTIAL
            elif controller_type in ("KPZ101", "TPZ001"):
                device_type = DeviceType.PIEZO
            else:
                device_type = DeviceType.MOTOR
            
            # Get saved config for this device
            device_config = controllers_config.get(str(serial), {})
            
            self.devices[serial] = DeviceInfo(
                serial=serial,
                controller_type=controller_type,
                channels=ctrl_info.get("channels", 1),
                device_type=device_type,
                config=device_config,
            )
        
        self._update_device_tree()
        self._update_device_tabs()
        
        self.statusBar().showMessage(f"Found {len(discovered)} device(s)")
    
    def _update_device_tree(self):
        """Update the device tree view."""
        self.device_tree.clear()
        
        # Group by type
        type_items = {}
        
        for device in self.devices.values():
            type_name = device.device_type.value
            if type_name not in type_items:
                type_item = QTreeWidgetItem([type_name])
                type_item.setExpanded(True)
                self.device_tree.addTopLevelItem(type_item)
                type_items[type_name] = type_item
            
            # Connection status icon
            status_icon = "🔴" if device.controller is None else "🟢"
            
            device_item = QTreeWidgetItem([
                f"{status_icon} {device.controller_type} - {device.serial}"
            ])
            device_item.setData(0, Qt.UserRole, device.serial)
            type_items[type_name].addChild(device_item)
    
    def _update_device_tabs(self):
        """Update the device tabs."""
        # Clear existing tabs
        self.device_tabs.clear()
        self.device_widgets.clear()
        
        for device in self.devices.values():
            widget = DeviceWidget(device)
            # Connect signals for individual device connect/disconnect
            widget.connect_requested.connect(self._on_device_connect_requested)
            widget.disconnect_requested.connect(self._on_device_disconnect_requested)
            self.device_widgets[device.serial] = widget
            self.device_tabs.addTab(
                widget, 
                f"{device.controller_type} ({device.serial})"
            )
            
            # Sync connection status from device info
            is_connected = device.controller is not None
            widget.update_connection_status(is_connected)
    
    def _on_device_connect_requested(self, serial: int):
        """Handle connect request from device widget."""
        if serial in self.devices:
            self._connect_device(self.devices[serial])
    
    def _on_device_disconnect_requested(self, serial: int):
        """Handle disconnect request from device widget."""
        if serial in self.devices:
            self._disconnect_device(self.devices[serial])
    
    def _on_device_selected(self, item: QTreeWidgetItem, column: int):
        """Handle device selection in tree."""
        serial = item.data(0, Qt.UserRole)
        if serial and serial in self.devices:
            # Switch to the corresponding tab
            for i in range(self.device_tabs.count()):
                if self.device_widgets.get(serial) == self.device_tabs.widget(i):
                    self.device_tabs.setCurrentIndex(i)
                    break
    
    def _show_context_menu(self, position):
        """Show context menu for device tree."""
        item = self.device_tree.itemAt(position)
        if not item:
            return
        
        serial = item.data(0, Qt.UserRole)
        if not serial or serial not in self.devices:
            return
        
        device = self.devices[serial]
        
        menu = QMenu()
        
        config_action = menu.addAction("⚙ Configure...")
        config_action.triggered.connect(lambda: self._configure_device(device))
        
        menu.addSeparator()
        
        if device.controller:
            disconnect_action = menu.addAction("⏏ Disconnect")
            disconnect_action.triggered.connect(lambda: self._disconnect_device(device))
        else:
            connect_action = menu.addAction("🔌 Connect")
            connect_action.triggered.connect(lambda: self._connect_device(device))
        
        menu.addSeparator()
        
        identify_action = menu.addAction("🔦 Identify")
        identify_action.triggered.connect(lambda: self._identify_device(device))
        
        menu.exec_(self.device_tree.mapToGlobal(position))
    
    def _configure_device(self, device: DeviceInfo, channel: int = 1):
        """Open configuration dialog for device."""
        # Remember connection state
        was_connected = device.controller is not None
        
        dialog = ConfigDialog(device, channel, self)
        if dialog.exec_() == QDialog.Accepted:
            device.config = dialog.get_config()
            
            # Save to config file
            full_config = load_device_config()
            if "controllers" not in full_config:
                full_config["controllers"] = {}
            full_config["controllers"][str(device.serial)] = device.config
            save_device_config(full_config)
            
            # Refresh UI but preserve connection state
            self._update_device_tree()
            self._update_device_tabs()
            
            # Restore connection status display
            if device.serial in self.device_widgets:
                self.device_widgets[device.serial].update_connection_status(was_connected)
                # Update position display if connected
                if was_connected and device.controller:
                    try:
                        status = device.controller.get_status()
                        self.device_widgets[device.serial].update_status(status)
                    except Exception:
                        pass
            
            self.statusBar().showMessage(f"Saved configuration for {device.serial}")
    
    def _connect_device(self, device: DeviceInfo):
        """Connect to a device."""
        try:
            self.statusBar().showMessage(f"Connecting to {device.serial}...")
            QApplication.processEvents()
            
            # For multi-channel devices (like KIM101), create a controller per channel
            # They share the same physical device connection but operate on different channels
            if device.channels > 1:
                # Create controllers for each channel
                device.channel_controllers = {}
                main_controller = None
                
                for ch in range(1, device.channels + 1):
                    controller = create_controller(device.serial, channel=ch)
                    
                    if ch == 1:
                        # First channel does the actual connect
                        if not controller.connect():
                            raise Exception("Connection returned False")
                        main_controller = controller
                        # For multi-channel devices sharing same hardware,
                        # subsequent controllers can share the device reference
                        device.controller = controller
                    else:
                        # For KIM101, all channels share the same device connection
                        # We need to share the _device reference
                        if hasattr(main_controller, '_device'):
                            controller._device = main_controller._device
                            controller._is_initialized = True
                            controller._set_state(main_controller.state)
                    
                    device.channel_controllers[ch] = controller
                
                self.statusBar().showMessage(f"Connected to {device.serial} ({device.channels} channels)")
            else:
                # Single-channel device
                controller = create_controller(device.serial, channel=1)
                
                if controller.connect():
                    device.controller = controller
                    self.statusBar().showMessage(f"Connected to {device.serial}")
                else:
                    raise Exception("Connection returned False")
            
            # Try to auto-detect stage type if not configured
            self._try_auto_detect_stage(device)
            
            # Update UI
            self._update_device_tree()
            if device.serial in self.device_widgets:
                self.device_widgets[device.serial].update_connection_status(True)
                # Immediately update position display
                try:
                    status = device.controller.get_status()
                    self.device_widgets[device.serial].update_status(status)
                except Exception:
                    pass
            
            # Start position update timer if not running
            if not self.update_timer.isActive():
                self.update_timer.start(500)
                
        except Exception as e:
            # Reset button state on error
            if device.serial in self.device_widgets:
                self.device_widgets[device.serial].update_connection_status(False)
            QMessageBox.warning(
                self, "Connection Error",
                f"Failed to connect to {device.serial}:\n{e}"
            )
            traceback.print_exc()
    
    def _disconnect_device(self, device: DeviceInfo):
        """Disconnect from a device."""
        if device.controller:
            try:
                device.controller.disconnect()
            except Exception:
                pass
            device.controller = None
            # Clear per-channel controllers too
            device.channel_controllers = {}
            self.statusBar().showMessage(f"Disconnected from {device.serial}")
            
            # Update UI
            self._update_device_tree()
            if device.serial in self.device_widgets:
                self.device_widgets[device.serial].update_connection_status(False)
            
            # Stop timer if no devices are connected
            any_connected = any(d.controller is not None for d in self.devices.values())
            if not any_connected and self.update_timer.isActive():
                self.update_timer.stop()
    
    def _identify_device(self, device: DeviceInfo):
        """Blink the LED on a device."""
        if device.controller:
            device.controller.identify()
        else:
            # Connect temporarily to identify
            try:
                controller = create_controller(device.serial, channel=1)
                controller.connect()
                controller.identify()
                time.sleep(1)
                controller.disconnect()
            except Exception as e:
                print(f"Identify failed: {e}")
    
    def _connect_all(self):
        """Connect to all devices."""
        for device in self.devices.values():
            if not device.controller:
                try:
                    self._connect_device(device)
                except Exception:
                    pass
        
        # Start status update timer
        self.update_timer.start(500)
    
    def _disconnect_all(self):
        """Disconnect from all devices."""
        self.update_timer.stop()
        
        for device in self.devices.values():
            self._disconnect_device(device)
    
    def _try_auto_detect_stage(self, device: DeviceInfo):
        """
        Try to auto-detect the stage type from the motor configuration.
        
        This reads the stage name from the Kinesis motor configuration
        which is stored in the device when a stage is assigned via Kinesis.
        """
        if not device.controller or not hasattr(device.controller, '_device'):
            return
        
        try:
            # Try to get motor configuration name from the device
            kinesis_device = device.controller._device
            if kinesis_device is None:
                return
            
            # The motor configuration is loaded during connect() via LoadMotorConfiguration
            # Try to get device settings info
            device_info = kinesis_device.GetDeviceInfo()
            if device_info is None:
                return
            
            # Check if there's a notes field or description that might contain stage info
            settings_name = ""
            
            # Try different ways to get the stage name
            try:
                # Method 1: Check MotorDeviceSettings
                motor_settings = kinesis_device.MotorDeviceSettings
                if motor_settings and hasattr(motor_settings, 'DeviceSettingsName'):
                    settings_name = str(motor_settings.DeviceSettingsName) if motor_settings.DeviceSettingsName else ""
            except Exception:
                pass
            
            if not settings_name:
                try:
                    # Method 2: Get from device notes
                    if hasattr(device_info, 'Notes'):
                        settings_name = str(device_info.Notes) if device_info.Notes else ""
                except Exception:
                    pass
            
            if not settings_name:
                try:
                    # Method 3: Device name sometimes contains stage info
                    if hasattr(device_info, 'Name'):
                        settings_name = str(device_info.Name) if device_info.Name else ""
                except Exception:
                    pass
            
            if settings_name:
                # Check if this stage is in our STAGES database
                from .stages import STAGES
                
                # Try exact match first
                stage_name = None
                if settings_name in STAGES:
                    stage_name = settings_name
                else:
                    # Try partial match (e.g., "DDS100/M" matches "DDS100")
                    settings_upper = settings_name.upper().replace("/M", "").replace("-M", "")
                    for known_stage in STAGES:
                        if known_stage.upper() in settings_upper or settings_upper in known_stage.upper():
                            stage_name = known_stage
                            break
                
                if stage_name:
                    # Update device config if not already set
                    channel_key = str(device.controller.channel)
                    if not device.config:
                        device.config = {"channels": {}}
                    if "channels" not in device.config:
                        device.config["channels"] = {}
                    if channel_key not in device.config["channels"]:
                        device.config["channels"][channel_key] = {}
                    
                    current_stage = device.config["channels"][channel_key].get("stage", "")
                    if not current_stage:
                        device.config["channels"][channel_key]["stage"] = stage_name
                        print(f"Auto-detected stage: {stage_name} for device {device.serial}")
                        
                        # Save to config file
                        full_config = load_device_config()
                        if "controllers" not in full_config:
                            full_config["controllers"] = {}
                        full_config["controllers"][str(device.serial)] = device.config
                        save_device_config(full_config)
        except Exception as e:
            # Silent failure - auto-detection is best-effort
            print(f"Stage auto-detection failed for {device.serial}: {e}")
    
    def _update_all_status(self):
        """Update status of all connected devices."""
        for device in self.devices.values():
            if device.controller:
                try:
                    if device.serial in self.device_widgets:
                        widget = self.device_widgets[device.serial]
                        
                        # For multi-channel devices, get status from each channel controller
                        if device.channel_controllers:
                            for ch, ctrl in device.channel_controllers.items():
                                try:
                                    status = ctrl.get_status()
                                    widget.update_channel_status(ch, status)
                                except Exception:
                                    pass
                        else:
                            # Single-channel device
                            status = device.controller.get_status()
                            widget.update_status(status)
                except Exception:
                    pass
    
    def _save_all_config(self):
        """Save all device configurations."""
        full_config = load_device_config()
        if "controllers" not in full_config:
            full_config["controllers"] = {}
        
        for device in self.devices.values():
            if device.config:
                full_config["controllers"][str(device.serial)] = device.config
        
        save_device_config(full_config)
        self.statusBar().showMessage("Configuration saved")
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About Thorlabs Motion Control",
            "<h3>Thorlabs Motion Control GUI</h3>"
            "<p>Unified controller interface for Thorlabs motion devices.</p>"
            "<p><b>Supported Controllers:</b></p>"
            "<ul>"
            "<li>KDC101 - K-Cube DC Servo</li>"
            "<li>KBD101 - K-Cube Brushless DC</li>"
            "<li>TDC001 - T-Cube DC Servo (legacy)</li>"
            "<li>KIM101 - K-Cube Piezo Inertia (4-ch)</li>"
            "<li>KPZ101 - K-Cube Piezo</li>"
            "</ul>"
            "<p>Uses Kinesis .NET (64-bit) or APT COM (32-bit) as backend.</p>"
            "<p><b>Author:</b> Weizmann Institute Ion Trap Lab</p>"
        )
    
    def closeEvent(self, event):
        """Clean up on close."""
        self.update_timer.stop()
        self._disconnect_all()
        event.accept()


def main():
    """Main entry point."""
    import sys
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = ThorlabsMotionControlGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
