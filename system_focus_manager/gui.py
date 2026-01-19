"""
Copyright © 2025 Manuela Riascos Hurtado
Original Author: Manuela Riascos Hurtado
Email: manhurta54@gmail.com
GitHub: https://github.com/Elah2022/system-focus-manager

Licensed under the MIT License.
Unauthorized removal of this copyright notice is prohibited.
"""



from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QMessageBox, QDialog,
    QSpinBox, QFormLayout, QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, Slot
from PySide6.QtGui import QFont, QPalette, QColor
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import psutil
import subprocess

# Copyright verification (DO NOT REMOVE - Required for application functionality)
_AUTHOR = "Manuela Riascos Hurtado"  # manhurta54@gmail.com
_COPYRIGHT = "Copyright © 2025 Manuela Riascos Hurtado"
_GITHUB = "https://github.com/Elah2022/system-focus-manager"
_LICENSE = "MIT"

def _verify_integrity():
    """Verifies application integrity and copyright information"""
    import base64
    _c = base64.b64decode(b"TWFudWVsYSBSaWFzY29zIEh1cnRhZG8=").decode()
    return _c == _AUTHOR

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent

    return base_path / relative_path

# Windows API for window management
try:
    import win32gui
    import win32process
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from process_manager import ProcessManager
from launcher import ApplicationLauncher
from logger import FocusLogger
from stats_manager import StatsManager
from config_window import ConfigWindow
from pin_manager import PINManager
from pin_dialog import PINDialog, SetPINDialog
from about_dialog import AboutDialog
from settings_manager import SettingsManager
from translations import lang

# Browser Focus Controller (optional)
try:
    from browser_focus import BrowserFocusController, BrowserFocusIntegration
    from browser_focus.monitor import BrowserMonitorThread
    from pathlib import Path
    BROWSER_CONTROL_AVAILABLE = True
except ImportError:
    BROWSER_CONTROL_AVAILABLE = False

# System Tray is optional
try:
    from system_tray import SystemTrayIcon
    SYSTEM_TRAY_AVAILABLE = True
except ImportError:
    SYSTEM_TRAY_AVAILABLE = False


def is_ultra_focus_active(mode_data: Dict) -> bool:
    """
    Check if Ultra Focus is actually configured and active.
    Returns True only if ultra_focus_settings exists AND has actual configuration.
    """
    if 'ultra_focus_settings' not in mode_data:
        return False

    ultra_settings = mode_data['ultra_focus_settings']

    # Check if it's an empty dict or has no meaningful configuration
    if not ultra_settings or not isinstance(ultra_settings, dict):
        return False

    # Ultra Focus is active if ANY of these are configured:
    # - Has a locked domain OR
    # - Use current domain is enabled OR
    # - Close all non-browser apps is enabled
    return bool(
        ultra_settings.get('locked_domain') or
        ultra_settings.get('use_current_domain') or
        ultra_settings.get('close_all_non_browser_apps')
    )


class ModeActivationWorker(QThread):
    """Thread worker to activate modes without blocking UI"""

    # Signals to communicate progress
    progress = Signal(str)  # Progress message
    finished = Signal(dict)  # Data whon finished: {closed_count, opened_count, session_id}
    error = Signal(str)  # Error message

    def __init__(self, mode_id, mode_data, process_manager, launcher, stats, browser_integrations, logger, main_pid, launcher_pid=None):
        super().__init__()
        self.mode_id = mode_id
        self.mode_data = mode_data
        self.process_manager = process_manager
        self.launcher = launcher
        self.stats = stats
        self.browser_integrations = browser_integrations
        self.logger = logger
        self.main_pid = main_pid  # Main GUI process PID
        self.launcher_pid = launcher_pid  # Launcher script PID (when running from python main.py)

    def run(self):
        """Execute heavy operations in background"""
        try:
            closed_count = 0
            opened_count = 0

            # Check whitelist status first
            whitelist_enabled = self.mode_data.get('whitelist_enabled', False)
            allowed_apps = self.mode_data.get('allowed_apps', [])

            # 1. Close specific applications (only if whitelist is NOT enabled)
            if not whitelist_enabled:
                apps_to_close = self.mode_data.get('close', [])
                if apps_to_close:
                    self.progress.emit(f"Closing {len(apps_to_close)} applications...")
                    for app in apps_to_close:
                        if self.process_manager.close_process(app):
                            self.stats.record_closed_app(app, self.mode_data['name'])
                            closed_count += 1

            # 1.5. Close non-whitelisted apps (only if whitelist is enabled)

            # If Ultra Focus, check if we should close all non-browser apps
            if is_ultra_focus_active(self.mode_data):
                ultra_settings = self.mode_data['ultra_focus_settings']
                selected_browser = ultra_settings.get('selected_browser', 'chrome')
                close_all_apps = ultra_settings.get('close_all_non_browser_apps', False)

                # Map browser name to executable
                browser_exe_map = {
                    'chrome': 'chrome.exe',
                    'brave': 'brave.exe',
                    'edge': 'msedge.exe'
                }

                # If close_all_non_browser_apps is enabled, force whitelist mode
                if close_all_apps:
                    # Only allow selected browser
                    allowed_apps = [browser_exe_map.get(selected_browser, 'chrome.exe')]

                    # Also allow FocusManager.exe to prevent closing itself
                    import sys
                    if getattr(sys, 'frozen', False):
                        # Running as compiled executable
                        allowed_apps.append('FocusManager.exe')

                    whitelist_enabled = True  # Force enable for Ultra Focus
                    self.logger.info(f"Ultra Focus: Closing all apps except {', '.join(allowed_apps)}")

            # Only apply whitelist if it's explicitly enabled
            if whitelist_enabled and allowed_apps:
                self.progress.emit("Closing unauthorized applications...")
                # Use ultra_strict mode for Ultra Focus to close almost everything
                is_ultra_focus = close_all_apps if 'close_all_apps' in locals() else False
                # Protect launcher PID if running from python main.py
                additional_pids = [self.launcher_pid] if self.launcher_pid else None
                whitelist_stats = self.process_manager.close_non_whitelisted_apps(allowed_apps, self.main_pid, additional_pids=additional_pids, ultra_strict=is_ultra_focus)
                closed_count += whitelist_stats['closed']
                self.logger.info(f"Whitelist: {whitelist_stats['closed']} closed, "
                                f"{whitelist_stats['allowed']} allowed, "
                                f"{whitelist_stats['protected']} protected")

            # 2. Open applications (only if whitelist is NOT enabled, or if Ultra Focus)
            apps_to_open = []

            # Ultra Focus always opens its browser (overrides whitelist)
            if is_ultra_focus_active(self.mode_data):
                apps_to_open = self.mode_data.get('open', [])
                ultra_settings = self.mode_data['ultra_focus_settings']
                selected_browser = ultra_settings.get('selected_browser', 'chrome')
                locked_domain = ultra_settings.get('locked_domain', '')

                # Filter to open ONLY the selected browser
                apps_to_open = [app for app in apps_to_open if app.get('name') == selected_browser]

                # If domain specified, add it as initial URL
                if locked_domain and apps_to_open:
                    app_config = apps_to_open[0].copy()
                    # Add URL as additional argument
                    url = f"https://{locked_domain}"
                    if 'args' not in app_config:
                        app_config['args'] = []
                    app_config['args'] = app_config['args'] + [url]
                    apps_to_open = [app_config]
                    self.progress.emit(f"Opening {selected_browser.capitalize()} on {locked_domain}...")
                else:
                    self.progress.emit(f"Opening {selected_browser.capitalize()} (Ultra Focus)...")
            else:
                # Normal Focus mode - always open apps from list (whitelist or not)
                apps_to_open = self.mode_data.get('open', [])
                if apps_to_open:
                    self.progress.emit(f"Opening {len(apps_to_open)} applications...")

            if apps_to_open:
                for app_config in apps_to_open:
                    if self.launcher.launch_application(app_config):
                        opened_count += 1

            # 3. Start session
            self.progress.emit("Recording session...")
            session_id = self.stats.start_session(self.mode_data['name'])
            self.stats.update_session_counts(session_id, closed_count, opened_count)

            # Log mode activation in audit log
            self.stats.log_mode_activation(self.mode_data['name'], session_id)

            # 4. Activate browser control (parallel with threads)
            if self.browser_integrations:
                self.progress.emit("Configuring browsers...")
                try:
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError
                    import time

                    def activate_single_browser(port, integration):
                        """Activate individual browser with timeout"""
                        try:
                            # Wait for browser to open
                            time.sleep(3)
                            integration.activate_mode(self.mode_data['name'])
                            return (port, True)
                        except Exception as e:
                            self.logger.error(f"Error activating browser on port {port}: {e}")
                            return (port, False)

                    # If Ultra Focus, only activate selected browser
                    integrations_to_activate = self.browser_integrations

                    if is_ultra_focus_active(self.mode_data):
                        ultra_settings = self.mode_data['ultra_focus_settings']
                        selected_browser = ultra_settings.get('selected_browser', 'chrome')

                        # Map browser to port
                        browser_port_map = {'chrome': 9222, 'brave': 9223, 'edge': 9224}
                        selected_port = browser_port_map.get(selected_browser)

                        if selected_port and selected_port in self.browser_integrations:
                            integrations_to_activate = {selected_port: self.browser_integrations[selected_port]}
                            self.progress.emit(f"Configurando {selected_browser.capitalize()} (Ultra Focus)...")

                    # Execute browser activation in parallel
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        futures = [
                            executor.submit(activate_single_browser, port, integration)
                            for port, integration in integrations_to_activate.items()
                        ]

                        # Wait for completion (no timeout - let them finish)
                        success_count = 0
                        for future in futures:
                            try:
                                port, success = future.result(timeout=10)
                                if success:
                                    success_count += 1
                            except TimeoutError:
                                self.logger.warning(f"Timeout activating browser")
                            except Exception as e:
                                self.logger.error(f"Error on browser activation: {e}")

                    self.logger.info(f"Browser control activated for {success_count}/{len(integrations_to_activate)} browsers")
                except Exception as e:
                    self.logger.error(f"Error activating browser control: {e}")

            # Emit successful result
            self.finished.emit({
                'session_id': session_id,
                'closed_count': closed_count,
                'opened_count': opened_count
            })

        except Exception as e:
            self.error.emit(f"Error activating mode: {str(e)}")


class ModeDeactivationWorker(QThread):
    """Thread worker to deactivate modes without blocking UI"""

    # Signals to communicate progress
    progress = Signal(str)  # Progress message
    finished = Signal()  # Signal whon finished
    error = Signal(str)  # Error message

    def __init__(self, session_id, session_start_time, mode_name, stats, browser_integrations, browser_monitors, logger, close_debug_browsers=False):
        super().__init__()
        self.session_id = session_id
        self.session_start_time = session_start_time
        self.mode_name = mode_name
        self.stats = stats
        self.browser_integrations = browser_integrations
        self.browser_monitors = browser_monitors
        self.logger = logger
        self.close_debug_browsers = close_debug_browsers

    def run(self):
        """Execute heavy deactivation operations in background"""
        try:
            # 1. End session
            if self.session_id:
                self.progress.emit("Ending session...")
                self.stats.end_session(self.session_id)

                # Calculate duration and log deactivation
                duration_minutes = 0
                if self.session_start_time:
                    duration = datetime.now() - self.session_start_time
                    duration_minutes = int(duration.total_seconds() / 60)
                    duration_str = f"{duration_minutes} minutes"
                    self.logger.session_ended(self.mode_name, duration_str)

                # ALWAYS log mode deactivation in audit log (even if duration is 0)
                self.stats.log_mode_deactivation(self.mode_name, self.session_id, duration_minutes)

            # 2. Deactivate Browser Focus Controllers for ALL browsers (parallel)
            if self.browser_integrations:
                self.progress.emit("Deactivating browsers...")
                try:
                    from concurrent.futures import ThreadPoolExecutor, as_completed

                    def deactivate_single_browser(port, integration):
                        """Deactivate individual browser"""
                        try:
                            integration.deactivate()
                            if port in self.browser_monitors:
                                self.browser_monitors[port].stop()
                            return True
                        except Exception as e:
                            self.logger.error(f"Error deactivating browser on port {port}: {e}")
                            return False

                    # Execute browser deactivation in parallel
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        futures = {
                            executor.submit(deactivate_single_browser, port, integration): port
                            for port, integration in self.browser_integrations.items()
                        }

                        # Wait for completion (max 3 second timeout)
                        for future in as_completed(futures, timeout=3):
                            try:
                                future.result()
                            except Exception as e:
                                self.logger.error(f"Error on browser deactivation: {e}")

                    self.logger.info(f"Browser control deactivated for {len(self.browser_integrations)} browsers")
                except Exception as e:
                    self.logger.error(f"Error deactivating browser control: {e}")

            # 3. Close debug browser processes if requested
            if self.close_debug_browsers:
                self.progress.emit("Closing debug browsers...")
                self._close_all_debug_browsers()

            # Emit completion signal
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Error deactivating mode: {str(e)}")

    def _close_all_debug_browsers(self):
        """Close all debug browser processes"""
        import psutil
        import time

        debug_browsers = ['chrome.exe', 'brave.exe', 'msedge.exe']
        closed_pids = []

        # Find all debug browser parent processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and proc.info['name'].lower() in debug_browsers:
                    # Check if it has --remote-debugging-port (debug browser)
                    if proc.info['cmdline']:
                        cmdline_str = ' '.join(proc.info['cmdline']).lower()
                        if '--remote-debugging-port' in cmdline_str:
                            # Found a debug browser parent process
                            try:
                                # Kill all children first
                                children = proc.children(recursive=True)
                                for child in children:
                                    try:
                                        child.kill()
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        pass

                                # Then kill the parent
                                proc.kill()
                                closed_pids.append((proc.info['name'], proc.info['pid']))
                                self.logger.info(f"🔓 Debug browser killed: {proc.info['name']} (PID {proc.info['pid']})")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if closed_pids:
            self.logger.info(f"🔓 Total debug browser instances closed: {len(closed_pids)}")
            # Wait a moment to ensure browsers are fully closed
            time.sleep(0.5)


class FocusManagerGUI(QMainWindow):
    """Main GUI interface for Focus Manager"""

    def __init__(self, launcher_pid=None):
        super().__init__()

        # Copyright verification (critical for application functionality)
        if not _verify_integrity():
            QMessageBox.critical(None, "Integrity Check Failed",
                "Application integrity verification failed.\nCopyright information may have been tampered with.")
            sys.exit(1)

        self.setWindowTitle("System Focus Manager")
        self.setFixedSize(550, 650)  # Fixed size, not resizable

        # Set window icon
        icon_path = get_resource_path('icons') / 'logo.svg'
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(icon_path)))

        # Initialize components
        self.settings_manager = SettingsManager()

        # Load saved language
        saved_language = self.settings_manager.get_language()
        lang.set_language(saved_language)

        self.logger = FocusLogger()
        self.process_manager = ProcessManager(self.logger)
        self.launcher = ApplicationLauncher(self.logger)
        self.stats = StatsManager()
        self.pin_manager = PINManager()

        # Save launcher PID to protect it from being closed (when running from python main.py)
        self.launcher_pid = launcher_pid

        # Initialize Browser Focus Controllers (one per browser)
        self.browser_controllers = {}  # {port: controller}
        self.browser_integrations = {}  # {port: integration}
        self.browser_monitors = {}  # {port: monitor}

        if BROWSER_CONTROL_AVAILABLE:
            try:
                # Load browser rules from AppData (persistent location)
                import os
                app_data = Path(os.getenv('LOCALAPPDATA')) / 'FocusManager'
                app_data.mkdir(parents=True, exist_ok=True)
                rules_path = app_data / 'rules.json'

                # Create controller for each supported browser
                from browser_focus.multi_browser import SUPPORTED_BROWSERS

                for browser_key, config in SUPPORTED_BROWSERS.items():
                    port = config['port']

                    # Create controller for this browser
                    controller = BrowserFocusController(debugging_port=port, logger=self.logger)
                    integration = BrowserFocusIntegration(controller)

                    # Load rules
                    if rules_path.exists():
                        integration.load_rules(str(rules_path))

                    # Initialize monitor (not started yet) - 1 second interval for fast response
                    monitor = BrowserMonitorThread(controller, interval=1)
                    monitor.set_block_callback(self.on_browser_block)
                    monitor.set_browser_closed_callback(lambda p=port: self.on_browser_closed_ultra_focus(p))

                    # Save
                    self.browser_controllers[port] = controller
                    self.browser_integrations[port] = integration
                    self.browser_monitors[port] = monitor

                self.logger.info(f"Browser Focus Controllers initialized for {len(SUPPORTED_BROWSERS)} browsers")
            except Exception as e:
                self.logger.error(f"Error initializing Browser Controllers: {e}")
                self.browser_controllers = {}

        # Initialize System Tray if available
        self.tray_icon = None
        if SYSTEM_TRAY_AVAILABLE:
            try:
                self.tray_icon = SystemTrayIcon(self)
            except Exception as e:
                self.logger.error(f"Error iniciando System Tray: {e}")
                self.tray_icon = None

        # Variables to track current state
        self.current_mode = None
        self.current_session_id = None
        self.session_start_time = None

        # Variables for strict blocking system
        self.strict_monitor_active = False
        self.blocked_apps = []

        # Variables for timer
        self.timer_active = False
        self.timer_minutes_left = 0
        self.timer_seconds_left = 0
        self.timer_mode_id = None

        # Pomodoro removed - keeping only simple timer

        # Worker threads for mode activation/deactivation
        self.activation_worker = None
        self.deactivation_worker = None

        # Variables for Ultra Focus Mode
        self.ultra_focus_active = False
        self.keyboard_blocker = None  # Initialized whon activating Ultra Focus

        # Save main process PID for protection
        self.main_pid = os.getpid()

        # Load all configured modes
        self.modes = self.load_modes()

        # Create visual interface
        self.create_widgets()

        # Start System Tray if available
        if self.tray_icon:
            try:
                self.tray_icon.start()
            except Exception as e:
                self.logger.error(f"Error iniciando System Tray: {e}")

        # Timer to update time (every 1 second for real-time display)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_time_display)
        self.update_timer.start(1000)  # 1 second for real-time updates

        # Timer for blocked apps monitor
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_blocked_apps)

        # Timer for timer countdown
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.timer_countdown)

    def load_modes(self) -> dict:
        """Load all modes from modes/ directory (persistent AppData location)"""
        import os
        import shutil

        # Use AppData for persistent mode storage
        app_data = Path(os.getenv('LOCALAPPDATA')) / 'FocusManager' / 'modes'
        app_data.mkdir(parents=True, exist_ok=True)

        # If AppData modes directory is empty, copy from bundled resources
        if not list(app_data.glob('*.json')):
            bundled_modes = get_resource_path('modes')
            if bundled_modes.exists():
                for json_file in bundled_modes.glob('*.json'):
                    shutil.copy2(json_file, app_data / json_file.name)
                self.logger.info("Copied default modes to AppData")

        # Now load from AppData (persistent location)
        modes = {}
        for json_file in app_data.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    mode_data = json.load(f)
                    mode_id = json_file.stem  # Name without extension
                    modes[mode_id] = mode_data
            except Exception as e:
                self.logger.error(f"Error loading mode {json_file}: {str(e)}")

        return modes

    def create_widgets(self):
        """Create all buttons and UI elements"""

        # Menu bar
        menubar = self.menuBar()
        help_menu = menubar.addMenu(lang.get('menu_help'))

        about_action = help_menu.addAction(lang.get('menu_about'))
        about_action.triggered.connect(self.show_about)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title - centered with logo
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #2c3e50; min-height: 30px;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 2, 10, 2)

        # Center container with logo and title
        center_container = QWidget()
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        # Logo SVG
        logo_path = Path(__file__).parent / 'icons' / 'logo.svg'
        if logo_path.exists():
            from PySide6.QtSvgWidgets import QSvgWidget
            logo_svg = QSvgWidget(str(logo_path))
            logo_svg.setFixedSize(24, 24)
            center_layout.addWidget(logo_svg)

        title_label = QLabel("System Focus Manager")
        title_label.setFont(QFont('Arial', 11, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        center_layout.addWidget(title_label)

        title_layout.addStretch()
        title_layout.addWidget(center_container)
        title_layout.addStretch()

        main_layout.addWidget(title_frame)

        # Current status - with visible border like mode selection
        self.status_group = QGroupBox(lang.get('current_status'))
        self.status_group.setFont(QFont('Arial', 11, QFont.Bold))
        self.status_group.setStyleSheet("QGroupBox { border: 1px solid #3498db; border-radius: 5px; padding: 15px 10px 10px 10px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; background-color: #2c3e50; color: white; }")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(10, 10, 10, 10)
        status_layout.setSpacing(5)

        # Layout horizontal para icono y texto de status
        self.status_h_layout = QHBoxLayout()
        self.status_h_layout.setAlignment(Qt.AlignCenter)

        # Widget for SVG icon (initially empty)
        self.status_icon_widget = QWidget()
        self.status_icon_layout = QHBoxLayout(self.status_icon_widget)
        self.status_icon_layout.setContentsMargins(0, 0, 0, 0)
        self.status_h_layout.addWidget(self.status_icon_widget)

        self.status_label = QLabel(lang.get('no_mode_active'))
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setStyleSheet("color: #7f8c8d;")
        self.status_h_layout.addWidget(self.status_label)

        status_layout.addLayout(self.status_h_layout)

        self.time_label = QLabel("")
        self.time_label.setFont(QFont('Arial', 9))
        self.time_label.setStyleSheet("color: #95a5a6;")
        self.time_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.time_label)

        self.status_group.setLayout(status_layout)
        main_layout.addWidget(self.status_group)

        # Mode buttons - Redesigned with visible border
        modes_group = QGroupBox(lang.get('select_mode'))
        modes_group.setFont(QFont('Arial', 11, QFont.Bold))
        modes_group.setStyleSheet("QGroupBox { border: 1px solid #3498db; border-radius: 5px; padding: 15px 10px 10px 10px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; background-color: #2c3e50; color: white; }")
        modes_layout = QGridLayout()
        modes_layout.setContentsMargins(10, 15, 10, 10)
        modes_layout.setSpacing(12)

        self.mode_buttons = {}
        row = 0
        col = 0

        for mode_id, mode_data in self.modes.items():
            # Create button with mode name only (no emoji)
            btn = QPushButton(mode_data['name'])
            btn.setFont(QFont('Arial', 12, QFont.Bold))
            btn.setMinimumHeight(90)
            btn.setMinimumWidth(220)
            btn.setStyleSheet("QPushButton { padding: 10px; border-radius: 5px; }")

            # Set icon from SVG file based on mode_id
            icon_filename_map = {
                'focus': 'focus.svg',
                'ultra_focus': 'ultrafocus.svg',
                # Add more modes as needed
            }

            icon_filename = icon_filename_map.get(mode_id, None)
            if icon_filename:
                icon_path = get_resource_path('icons') / icon_filename
                if icon_path.exists():
                    from PySide6.QtGui import QIcon
                    from PySide6.QtCore import QSize
                    btn.setIcon(QIcon(str(icon_path)))
                    btn.setIconSize(QSize(32, 32))

            btn.clicked.connect(lambda checked, m=mode_id: self.activate_mode(m))
            modes_layout.addWidget(btn, row, col)

            self.mode_buttons[mode_id] = btn

            col += 1
            if col > 1:  # 2 columns instead of 3
                col = 0
                row += 1

        modes_group.setLayout(modes_layout)
        main_layout.addWidget(modes_group)

        # Action buttons with icons
        action_layout = QHBoxLayout()

        # Deactivate mode button (without icon)
        self.deactivate_btn = QPushButton(lang.get('deactivate_btn'))
        self.deactivate_btn.setFont(QFont('Arial', 11, QFont.Bold))
        self.deactivate_btn.setMinimumHeight(50)
        self.deactivate_btn.setStyleSheet("background-color: #95a5a6; color: white;")
        self.deactivate_btn.setEnabled(False)
        self.deactivate_btn.clicked.connect(self.deactivate_mode)
        action_layout.addWidget(self.deactivate_btn)

        # Timer button (without icon)
        self.timer_btn = QPushButton(lang.get('timer_btn'))
        self.timer_btn.setFont(QFont('Arial', 11, QFont.Bold))
        self.timer_btn.setMinimumHeight(50)
        self.timer_btn.setStyleSheet("background-color: #95a5a6; color: white;")
        self.timer_btn.setEnabled(False)
        self.timer_btn.clicked.connect(self.set_timer)
        action_layout.addWidget(self.timer_btn)

        # Statistics button (without icon)
        stats_btn = QPushButton(lang.get('stats_btn'))
        stats_btn.setFont(QFont('Arial', 11, QFont.Bold))
        stats_btn.setMinimumHeight(50)
        stats_btn.setStyleSheet("background-color: #3498db; color: white;")
        stats_btn.clicked.connect(self.show_stats)
        action_layout.addWidget(stats_btn)

        # Configuration button (without icon)
        config_btn = QPushButton(lang.get('configure_btn'))
        config_btn.setFont(QFont('Arial', 11, QFont.Bold))
        config_btn.setMinimumHeight(50)
        config_btn.setStyleSheet("background-color: #3498db; color: white;")
        config_btn.clicked.connect(self.show_config)
        action_layout.addWidget(config_btn)

        main_layout.addLayout(action_layout)

    def activate_mode(self, mode_id: str):
        """Activate a mode and automatically close/opon applications"""

        # If mode is already active, deactivate it (toggle)
        if self.current_mode == mode_id:
            self.deactivate_mode()
            return

        # If parental mode is active and there's an active mode, request PIN
        if self.current_mode and self.pin_manager.is_parental_mode():
            if not self.verify_pin_access("change mode"):
                return  # Incorrect PIN, don't change

        # If there's already an active mode, deactivate it first
        if self.current_mode:
            self.deactivate_mode(silent=True)

        mode_data = self.modes[mode_id]

        # Prepare message with apps to close/open
        apps_to_close = mode_data.get('close', [])
        apps_to_open = mode_data.get('open', [])
        whitelist_enabled = mode_data.get('whitelist_enabled', False)
        allowed_apps = mode_data.get('allowed_apps', [])

        # Build message based on whether whitelist is enabled
        if whitelist_enabled and allowed_apps:
            # WHITELIST MODE: Show allowed apps instead of apps to close/open
            allowed_names = ", ".join([app.replace('.exe', '') for app in allowed_apps])
            if len(allowed_names) > 50:
                allowed_list = allowed_names[:47] + "..."
            else:
                allowed_list = allowed_names

            will_allow = "Solo se permitirán:" if lang.get_current_language() == 'es' else "Only these apps will be allowed:"
            will_block = "Todo lo demás será bloqueado" if lang.get_current_language() == 'es' else "Everything else will be blocked"

            message = f"{lang.get('confirm_activation_message', mode=mode_data['name'])}\n\n{will_allow}\n{allowed_list}\n\n{will_block}"
        else:
            # NORMAL MODE: Show apps to close/open
            # Format list of apps to close
            close_list = ""
            if apps_to_close:
                close_names = ", ".join([app.replace('.exe', '') for app in apps_to_close])
                if len(close_names) > 30:
                    close_list = close_names[:27] + "..."
                else:
                    close_list = close_names
            else:
                close_list = "Ninguna" if lang.get_current_language() == 'es' else "None"

            # Format list of apps to open
            open_list = ""
            if apps_to_open:
                open_names = ", ".join([app.get('name', '') for app in apps_to_open])
                if len(open_names) > 30:
                    open_list = open_names[:27] + "..."
                else:
                    open_list = open_names
            else:
                open_list = "Ninguna" if lang.get_current_language() == 'es' else "None"

            will_close = "Cerrará:" if lang.get_current_language() == 'es' else "Will close:"
            will_open = "Abrirá:" if lang.get_current_language() == 'es' else "Will open:"

            message = f"{lang.get('confirm_activation_message', mode=mode_data['name'])}\n\n{will_close}\n{close_list}\n\n{will_open}\n{open_list}"

        # Confirm change
        reply = QMessageBox.question(
            self,
            lang.get('confirm_activation', mode=mode_data['name']),
            message,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Update PRE-activation state (so UI shows it's activating)
        self.current_mode = mode_id
        self.session_start_time = datetime.now()
        activating_text = "ACTIVANDO..." if lang.get_current_language() == 'es' else "ACTIVATING..."
        self.status_label.setText(f"{mode_data['name']} {activating_text}")
        self.status_label.setFont(QFont('Arial', 14, QFont.Bold))
        self.status_label.setStyleSheet("color: white;")

        # Crear y configurar el worker thread
        self.activation_worker = ModeActivationWorker(
            mode_id,
            mode_data,
            self.process_manager,
            self.launcher,
            self.stats,
            self.browser_integrations,
            self.logger,
            os.getpid(),  # Main process PID
            self.launcher_pid  # Launcher script PID (if running from python main.py)
        )

        # Connect signals
        self.activation_worker.progress.connect(self.on_activation_progress)
        self.activation_worker.finished.connect(lambda result: self.on_activation_finished(mode_id, mode_data, result))
        self.activation_worker.error.connect(self.on_activation_error)

        # Start the worker
        self.activation_worker.start()

    def on_activation_progress(self, message: str):
        """Update progress message during activation"""
        self.time_label.setText(f"⏳ {message}")

    def on_activation_finished(self, mode_id: str, mode_data: dict, result: dict):
        """Callback whon activation finishes successfully"""
        # Extract results
        session_id = result['session_id']

        # Update state
        self.current_session_id = session_id

        # Activate app monitoring (only if whitelist is NOT enabled)
        # Whon whitelist is enabled, the whitelist handles all app control
        whitelist_enabled = mode_data.get('whitelist_enabled', False)
        if not whitelist_enabled:
            apps_to_close = mode_data.get('close', [])
            if apps_to_close:
                self.blocked_apps = apps_to_close.copy()
                self.strict_monitor_active = True
                # Start monitor every 10 seconds
                self.monitor_timer.start(10000)
                self.logger.info(f"Monitoring activated - Blocked apps: {', '.join(self.blocked_apps)}")
        else:
            # If whitelist is enabled, activate monitoring for whitelist enforcement
            self.strict_monitor_active = True
            self.monitor_timer.start(10000)
            self.logger.info("Monitoreo de whitelist activado")

        # Start browser monitoring
        if self.browser_integrations:
            # If Ultra Focus, only monitor selected browser
            if is_ultra_focus_active(mode_data):
                ultra_settings = mode_data['ultra_focus_settings']
                selected_browser = ultra_settings.get('selected_browser', 'chrome')
                browser_port_map = {'chrome': 9222, 'brave': 9223, 'edge': 9224}
                selected_port = browser_port_map.get(selected_browser)

                if selected_port and selected_port in self.browser_monitors:
                    self.browser_monitors[selected_port].start()
                    self.logger.info(f"Monitoreo de {selected_browser.capitalize()} activado")
            else:
                # Normal mode: monitor all browsers
                for port in self.browser_monitors.keys():
                    if port in self.browser_monitors:
                        self.browser_monitors[port].start()
                self.logger.info(f"Monitoreo de browsers activado para {len(self.browser_integrations)} browsers")

        # Activate Ultra Focus Mode ONLY if this is the ultra_focus mode AND has valid config
        if mode_id == 'ultra_focus' and is_ultra_focus_active(mode_data):
            self._activate_ultra_focus(mode_data)

        # Update UI
        self.update_status_display()
        self.highlight_active_mode(mode_id)
        self.deactivate_btn.setEnabled(True)
        self.deactivate_btn.setStyleSheet("background-color: #3498db; color: white;")
        self.timer_btn.setEnabled(True)
        self.timer_btn.setStyleSheet("background-color: #3498db; color: white;")

        self.logger.session_started(mode_data['name'])

        # Clear progress message
        self.time_label.setText("")

        # Update system tray menu to reflect mode activation
        if self.tray_icon:
            self.tray_icon.update_menu()

    def on_activation_error(self, error_message: str):
        """Callback whon there's an error during activation"""
        self.logger.error(error_message)
        QMessageBox.critical(self, "Error", error_message)

        # Reset state
        self.current_mode = None
        self.current_session_id = None
        self.session_start_time = None
        self.update_status_display()

    def deactivate_mode(self, silent=False):
        """Deactivate current mode and save session statistics"""

        if not self.current_mode:
            if not silent:
                QMessageBox.information(self, "Info", "No active mode")
            return

        # Get current mode data
        mode_data = self.modes.get(self.current_mode)

        # Verify PIN only if strict_mode is active in this mode AND parental mode is enabled
        requires_pin = mode_data.get('strict_mode', False) and self.pin_manager.is_parental_mode()

        if requires_pin and not silent:
            # If timer is active, mention that
            if self.timer_active:
                if not self.verify_pin_access("Deactivate Mode (timer active)"):
                    return  # Incorrect PIN, don't deactivate
            else:
                if not self.verify_pin_access("Deactivate Mode"):
                    return  # Incorrect PIN, don't deactivate

        # Save information before deactivating
        mode_name = self.modes[self.current_mode]['name']
        session_id = self.current_session_id
        session_start = self.session_start_time

        # Show deactivation state
        deactivating_text = "DESACTIVANDO..." if lang.get_current_language() == 'es' else "DEACTIVATING..."
        self.status_label.setText(deactivating_text)
        self.status_label.setStyleSheet("color: white;")

        # Deactivate strict blocking system IMMEDIATELY (non-blocking)
        self.strict_monitor_active = False
        self.blocked_apps = []
        self.monitor_timer.stop()

        # Deactivate timer IMMEDIATELY (non-blocking)
        self.timer_active = False
        self.timer_minutes_left = 0
        self.timer_mode_id = None
        self.countdown_timer.stop()

        # Create and configure worker thread for heavy operations
        self.deactivation_worker = ModeDeactivationWorker(
            session_id,
            session_start,
            mode_name,
            self.stats,
            self.browser_integrations,
            self.browser_monitors,
            self.logger,
            close_debug_browsers=True  # Close debug browsers when deactivating Focus mode
        )

        # Connect signals
        self.deactivation_worker.progress.connect(self.on_deactivation_progress)
        self.deactivation_worker.finished.connect(self.on_deactivation_finished)
        self.deactivation_worker.error.connect(self.on_deactivation_error)

        # Start worker
        self.deactivation_worker.start()

    def on_deactivation_progress(self, message: str):
        """Update progress message during deactivation"""
        self.time_label.setText(message)

    def on_deactivation_finished(self):
        """Callback whon deactivation finishes successfully"""
        # Deactivate Ultra Focus if it was active
        if self.ultra_focus_active:
            self._deactivate_ultra_focus()

        # Reset state
        self.current_mode = None
        self.current_session_id = None
        self.session_start_time = None

        # Update UI
        self.update_status_display()
        self.highlight_active_mode(None)
        self.deactivate_btn.setEnabled(False)
        self.deactivate_btn.setStyleSheet("background-color: #95a5a6; color: white;")
        self.timer_btn.setEnabled(False)
        self.timer_btn.setText("Timer")
        self.timer_btn.setStyleSheet("background-color: #95a5a6; color: white;")

        # Clear progress message
        self.time_label.setText("")

        # Update system tray menu to reflect mode deactivation
        if self.tray_icon:
            self.tray_icon.update_menu()

    def on_deactivation_error(self, error_message: str):
        """Callback whon there's an error during deactivation"""
        self.logger.error(error_message)
        QMessageBox.critical(self, "Error", error_message)

        # Evon so, reset state
        self.current_mode = None
        self.current_session_id = None
        self.session_start_time = None
        self.update_status_display()

    def highlight_active_mode(self, mode_id: Optional[str]):
        """Highlight in greon the button of the active mode"""
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize

        # Reset all buttons to default icons
        for btn_mode_id, btn in self.mode_buttons.items():
            btn.setStyleSheet("")

            # Restore default icon
            icon_filename_map = {
                'focus': 'focus.svg',
                'ultra_focus': 'ultrafocus.svg',
            }

            icon_filename = icon_filename_map.get(btn_mode_id)
            if icon_filename:
                icon_path = Path(__file__).parent / 'icons' / icon_filename
                if icon_path.exists():
                    btn.setIcon(QIcon(str(icon_path)))
                    btn.setIconSize(QSize(32, 32))

        # Highlight active and change icon
        if mode_id and mode_id in self.mode_buttons:
            self.mode_buttons[mode_id].setStyleSheet("background-color: #3498db; color: white;")

            # Change to active icon
            active_icon_map = {
                'focus': 'focus_activado.svg',
                'ultra_focus': 'ultrafocusnegro.svg',
            }

            active_icon_filename = active_icon_map.get(mode_id)
            if active_icon_filename:
                active_icon_path = Path(__file__).parent / 'icons' / active_icon_filename
                if active_icon_path.exists():
                    self.mode_buttons[mode_id].setIcon(QIcon(str(active_icon_path)))
                    self.mode_buttons[mode_id].setIconSize(QSize(32, 32))

    def update_status_display(self):
        """Update what's displayed on screon according to the active mode"""

        # Clear previous icon
        for i in reversed(range(self.status_icon_layout.count())):
            self.status_icon_layout.itemAt(i).widget().setParent(None)

        if self.current_mode:
            mode_data = self.modes[self.current_mode]
            active_text = "ACTIVE" if lang.get_current_language() == 'en' else "ACTIVO"

            # Add SVG icon based on mode
            icon_path = None
            if self.current_mode == 'focus':
                icon_path = Path(__file__).parent / 'icons' / 'focus.svg'
            elif self.current_mode == 'ultrafocus':
                icon_path = Path(__file__).parent / 'icons' / 'ultrafocus.svg'

            if icon_path and icon_path.exists():
                from PySide6.QtSvgWidgets import QSvgWidget
                icon_svg = QSvgWidget(str(icon_path))
                icon_svg.setFixedSize(24, 24)
                self.status_icon_layout.addWidget(icon_svg)

            self.status_label.setText(f"{mode_data['name']} {active_text}")
            self.status_label.setFont(QFont('Arial', 14, QFont.Bold))
            self.status_label.setStyleSheet("color: #3498db;")
        else:
            self.status_label.setText(lang.get('no_mode_active'))
            self.status_label.setFont(QFont('Arial', 12))
            self.status_label.setStyleSheet("color: #7f8c8d;")
            self.time_label.setText("")

    def update_time_display(self):
        """Update every second the time I've beon in the current mode"""

        if self.current_mode and self.session_start_time:
            elapsed = datetime.now() - self.session_start_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)

            time_text = f"{lang.get('time_in_mode')} {hours}h {minutes:02d}m {seconds:02d}s"

            # Add timer info if active
            if self.timer_active and self.timer_seconds_left > 0:
                minutes = self.timer_seconds_left // 60
                seconds = self.timer_seconds_left % 60
                timer_text = lang.get('timer_remaining', time=f"{minutes:02d}:{seconds:02d}")
                time_text += f"\n{timer_text}"

            self.time_label.setText(time_text)

    def set_timer(self):
        """Activate or cancel the timer for the current mode"""
        if not self.current_mode:
            QMessageBox.warning(self, lang.get('no_mode_active_for_timer'), lang.get('activate_mode_first'))
            return

        # If timer is already active, cancel it
        if self.timer_active:
            # Verify PIN if parental mode is active
            if self.pin_manager.is_parental_mode():
                if not self.verify_pin_access("cancel the timer"):
                    return  # Incorrect PIN, don't cancel

            # Cancel timer
            self.timer_active = False
            self.timer_seconds_left = 0
            self.timer_minutes_left = 0
            self.timer_mode_id = None
            self.countdown_timer.stop()
            self.timer_btn.setText(lang.get('timer_btn'))
            self.logger.info("Timer cancelado")
            return

        # Window to select timer type
        dialog = QDialog(self)
        dialog.setWindowTitle(lang.get('timer_btn'))
        dialog.setMinimumSize(500, 400)

        # Set window icon
        timer_icon_path = Path(__file__).parent / 'icons' / 'timer.svg'
        if timer_icon_path.exists():
            from PySide6.QtGui import QIcon
            dialog.setWindowIcon(QIcon(str(timer_icon_path)))

        layout = QVBoxLayout()

        # Title with timer icon
        title_layout = QHBoxLayout()
        title_layout.addStretch()

        timer_svg_path = Path(__file__).parent / 'icons' / 'timer.svg'
        if timer_svg_path.exists():
            from PySide6.QtSvgWidgets import QSvgWidget
            timer_svg = QSvgWidget(str(timer_svg_path))
            timer_svg.setFixedSize(28, 28)
            title_layout.addWidget(timer_svg)

        title = QLabel(lang.get('select_timer_type'))
        title.setFont(QFont('Arial', 14, QFont.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        # Botones para elegir tipo
        type_layout = QHBoxLayout()

        # Only simple timer (Pomodoro removed)
        simple_btn = QPushButton(lang.get('configure_timer'))
        simple_btn.setFont(QFont('Arial', 12, QFont.Bold))
        simple_btn.setMinimumHeight(80)
        simple_btn.setStyleSheet("background-color: #3498db; color: white;")
        simple_btn.clicked.connect(lambda: self._show_simple_timer_config(dialog))
        layout.addWidget(simple_btn)

        # Description
        simple_desc = QLabel(lang.get('timer_description'))
        simple_desc.setFont(QFont('Arial', 10))
        simple_desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(simple_desc)

        # Cancel button
        cancel_btn = QPushButton(lang.get('cancel'))
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def _show_simple_timer_config(self, parent_dialog):
        """Shows simple timer configuration"""
        parent_dialog.accept()

        dialog = QDialog(self)
        dialog.setWindowTitle(lang.get("timer_simple"))
        dialog.setMinimumSize(450, 320)

        # Set window icon
        timer_icon_path = Path(__file__).parent / 'icons' / 'timer.svg'
        if timer_icon_path.exists():
            from PySide6.QtGui import QIcon
            dialog.setWindowIcon(QIcon(str(timer_icon_path)))

        layout = QVBoxLayout()

        # Title with timer icon
        title_layout = QHBoxLayout()
        title_layout.addStretch()

        # Timer SVG icon
        timer_svg_path = Path(__file__).parent / 'icons' / 'timer.svg'
        if timer_svg_path.exists():
            from PySide6.QtSvgWidgets import QSvgWidget
            timer_svg = QSvgWidget(str(timer_svg_path))
            timer_svg.setFixedSize(32, 32)
            title_layout.addWidget(timer_svg)

        title = QLabel(lang.get("timer_simple"))
        title.setFont(QFont('Arial', 14, QFont.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()

        layout.addLayout(title_layout)

        desc1 = QLabel(lang.get("how_many_minutes"))
        desc1.setFont(QFont('Arial', 11))
        desc1.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc1)

        desc2 = QLabel(lang.get("mode_will_deactivate"))
        desc2.setFont(QFont('Arial', 9))
        desc2.setStyleSheet("color: #7f8c8d;")
        desc2.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc2)

        timer_spin = QSpinBox()
        timer_spin.setMinimum(1)
        timer_spin.setMaximum(480)
        timer_spin.setValue(25)
        timer_spin.setFont(QFont('Arial', 16, QFont.Bold))
        timer_spin.setAlignment(Qt.AlignCenter)
        timer_spin.setStyleSheet("""
            QSpinBox {
                min-height: 50px;
                padding-right: 25px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
            }
        """)
        layout.addWidget(timer_spin)

        btn_layout = QHBoxLayout()

        ok_btn = QPushButton(lang.get("activate"))
        ok_btn.setFont(QFont('Arial', 11, QFont.Bold))
        ok_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        ok_btn.clicked.connect(lambda: self.start_timer(timer_spin.value(), dialog))
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def start_timer(self, minutes, dialog):
        """Start simple timer"""
        self.timer_minutes_left = minutes
        self.timer_seconds_left = minutes * 60  # Convert to seconds
        self.timer_active = True
        self.timer_mode_id = self.current_mode
        dialog.accept()
        # Start countdown every second
        self.countdown_timer.start(1000)  # 1 second instead of 60000
        self.logger.info(f"Timer activated: {minutes} minutes")
        # Actualizar texto del botón with time format
        self.update_timer_display()

    def timer_countdown(self):
        """Here I handle the timer countdown every second"""
        # Timer normal
        if self.timer_active and self.current_mode:
            # Subtract one second
            self.timer_seconds_left -= 1

            # Update minutes left for compatibility
            self.timer_minutes_left = self.timer_seconds_left // 60

            # Actualizar botón y display
            self.update_timer_display()
            self.update_time_display()

            if self.timer_seconds_left <= 0:
                # Timer finished, deactivate the mode
                self.logger.info(f"Timer finished for mode {self.modes[self.current_mode]['name']}")
                self.timer_btn.setText("Timer")
                self.timer_active = False
                self.deactivate_mode(silent=True)
                return

    def update_timer_display(self):
        """Update the timer button text with mm:ss format"""
        if self.timer_active and self.timer_seconds_left > 0:
            minutes = self.timer_seconds_left // 60
            seconds = self.timer_seconds_left % 60
            self.timer_btn.setText(f"{minutes:02d}:{seconds:02d}")
        else:
            self.timer_btn.setText("Timer")

    def _capture_browser_tabs(self) -> List[Dict]:
        """Capture all opon browser tabs with exact URLs"""
        tabs = []

        if not BROWSER_CONTROL_AVAILABLE:
            return tabs

        self.logger.info(f"📊 Capturing tabs from {len(self.browser_controllers)} browsers: puertos {list(self.browser_controllers.keys())}")

        try:
            for port, controller in self.browser_controllers.items():
                try:
                    # Get all tabs from this browser
                    browser_tabs = controller.get_open_tabs()
                    self.logger.info(f"  Puerto {port}: {len(browser_tabs)} tabs encontrados")

                    for tab in browser_tabs:
                        tab_url = tab.get('url', '')

                        # Skip system pages during capture (NO guardar chrome://newtab, about:blank, etc.)
                        if (tab_url.startswith('chrome://') or
                            tab_url.startswith('edge://') or
                            tab_url.startswith('brave://') or
                            tab_url.startswith('about:') or
                            tab_url.startswith('chrome-extension://') or
                            not tab_url):
                            self.logger.info(f"  ⏭️ NO se guarda system page: {tab_url[:40]}")
                            continue

                        tab_info = {
                            'port': port,
                            'url': tab_url,
                            'title': tab.get('title', ''),
                            'tab_id': tab.get('id', '')
                        }

                        # Try to get scroll position and media time via CDP WebSocket
                        try:
                            ws_url = tab.get('webSocketDebuggerUrl')
                            if ws_url:
                                import websocket
                                import json as json_lib

                                ws = websocket.create_connection(ws_url, timeout=1)

                                # Get scroll position
                                scroll_cmd = {
                                    "id": 1,
                                    "method": "Runtime.evaluate",
                                    "params": {
                                        "expression": "JSON.stringify({scrollX: window.scrollX, scrollY: window.scrollY})"
                                    }
                                }
                                ws.send(json_lib.dumps(scroll_cmd))
                                response = ws.recv()
                                result = json_lib.loads(response)

                                if 'result' in result and 'result' in result['result']:
                                    scroll_data = json_lib.loads(result['result']['result']['value'])
                                    tab_info['scroll_x'] = scroll_data.get('scrollX', 0)
                                    tab_info['scroll_y'] = scroll_data.get('scrollY', 0)

                                # Get media time
                                media_cmd = {
                                    "id": 2,
                                    "method": "Runtime.evaluate",
                                    "params": {
                                        "expression": """(function() {
                                            var video = document.querySelector('video');
                                            var audio = document.querySelector('audio');
                                            var media = video || audio;
                                            if (media) {
                                                return JSON.stringify({
                                                    currentTime: media.currentTime,
                                                    duration: media.duration,
                                                    paused: media.paused
                                                });
                                            }
                                            return null;
                                        })()"""
                                    }
                                }
                                ws.send(json_lib.dumps(media_cmd))
                                response = ws.recv()
                                result = json_lib.loads(response)

                                if 'result' in result and 'result' in result['result'] and result['result']['result'].get('value'):
                                    media_data = json_lib.loads(result['result']['result']['value'])
                                    tab_info['media_time'] = media_data.get('currentTime', 0)
                                    tab_info['media_duration'] = media_data.get('duration', 0)
                                    tab_info['media_paused'] = media_data.get('paused', True)

                                ws.close()
                        except Exception as e:
                            # It's OK if we can't get detailed state, we'll still save the URL
                            pass

                        tabs.append(tab_info)

                except Exception as e:
                    self.logger.warning(f"Error capturing tabs from port {port}: {e}")
        except Exception as e:
            self.logger.error(f"Error capturing browser tabs: {e}")

        return tabs

    def _restore_browser_tabs(self, tabs: List[Dict]):
        """
        Restore browser tabs to existing browser windows.
        This function is called with a delay to ensure browsers are ready.
        """
        if not tabs or not BROWSER_CONTROL_AVAILABLE:
            self.logger.warning("❌ Cannot restore tabs: no tabs or BROWSER_CONTROL not available")
            return

        restored_count = 0
        self.logger.info(f"🔄 Restoring {len(tabs)} browser tabs...")
        self.logger.info(f"📊 Available controllers: {list(self.browser_controllers.keys())}")

        for tab_info in tabs:
            try:
                port = tab_info.get('port')
                url = tab_info.get('url', '')

                self.logger.info(f"  Intentando restaurar: puerto={port}, url={url[:60] if url else 'None'}...")

                if not url or not port:
                    self.logger.warning(f"  ❌ Skipping: URL o puerto faltante")
                    continue

                controller = self.browser_controllers.get(port)
                if not controller:
                    self.logger.warning(f"  ❌ No hay controller para puerto {port}")
                    self.logger.warning(f"  Available controllers: {list(self.browser_controllers.keys())}")
                    continue

                # Check if browser is available by checking if it has any tabs
                try:
                    current_tabs = controller.get_open_tabs()
                    self.logger.info(f"  Puerto {port} has {len(current_tabs)} current tabs")
                except Exception as e:
                    self.logger.warning(f"  ❌ Error obteniendo tabs del puerto {port}: {e}")
                    continue

                # Opon new tab with URL
                self.logger.info(f"  Opening tab on puerto {port}...")
                if controller.open_new_tab(url):
                    restored_count += 1
                    self.logger.info(f"  ✅ Tab restaurado: {url[:50]}...")

                    # Add to recently restored list (browser monitor will ignore these for 10 seconds)
                    self.recently_restored_urls.append(url)
                    self.logger.info(f"  🛡️ Protecting restored tab from monitor for 10 seconds")

                    # Remove from protected list after 10 seconds
                    QTimer.singleShot(10000, lambda u=url: self._unprotect_restored_tab(u))

                    # Verify tab was actually created (wait a bit for it to appear)
                    QTimer.singleShot(500, lambda p=port, u=url: self._verify_tab_restored(p, u))

                    # Schedule scroll and media restore after page loads
                    if tab_info.get('scroll_x') is not None or tab_info.get('media_time') is not None:
                        # Wait 2 seconds for page to load, thon restore state
                        QTimer.singleShot(2000, lambda ti=tab_info, p=port: self._restore_tab_state(ti, p))
                else:
                    self.logger.warning(f"  ❌ Failed to opon tab: {url[:50]}...")

            except Exception as e:
                self.logger.warning(f"Error restaurando tab: {e}")

        self.logger.info(f"Tabs restaurados: {restored_count}/{len(tabs)}")

    def _unprotect_restored_tab(self, url: str):
        """Remove URL from protection list after 10 seconds"""
        if url in self.recently_restored_urls:
            self.recently_restored_urls.remove(url)
            self.logger.info(f"  🛡️ Protection removed for: {url[:60]}")

    def _verify_tab_restored(self, port: int, url: str):
        """Verify that the tab was actually created after restoring it"""
        try:
            controller = self.browser_controllers.get(port)
            if not controller:
                return

            current_tabs = controller.get_open_tabs()
            tab_found = False

            for tab in current_tabs:
                tab_url = tab.get('url', '')
                # Check if URL matches (compare base URL without query params)
                base_url = url.split('?')[0].split('#')[0]
                tab_base_url = tab_url.split('?')[0].split('#')[0]

                if base_url in tab_url or tab_base_url in url:
                    tab_found = True
                    self.logger.info(f"  ✓ Verified: Tab exists in browser - {url[:60]}")
                    break

            if not tab_found:
                self.logger.warning(f"  ⚠️ WARNING: Tab NOT found after restore - {url[:60]}")
                self.logger.warning(f"  Tabs actuales on puerto {port}: {[t.get('url', '')[:40] for t in current_tabs]}")

        except Exception as e:
            self.logger.warning(f"  Error verificando tab restaurado: {e}")

    def _capture_window_positions(self) -> List[Dict]:
        """Capture all window positions and sizes"""
        windows = []

        if not WIN32_AVAILABLE:
            return windows

        def enum_window_callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    # Get window title
                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        return True

                    # Get process ID
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)

                    # Get process name
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                    except:
                        process_name = "Unknown"

                    # Get window rectangle (position and size)
                    rect = win32gui.GetWindowRect(hwnd)
                    x, y, right, bottom = rect
                    width = right - x
                    height = bottom - y

                    window_info = {
                        'hwnd': hwnd,
                        'title': title,
                        'process_name': process_name,
                        'pid': pid,
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height
                    }

                    windows_list.append(window_info)
                except Exception as e:
                    pass

            return True

        try:
            win32gui.EnumWindows(enum_window_callback, windows)
        except Exception as e:
            self.logger.error(f"Error capturando posiciones de ventanas: {e}")

        return windows

    def _capture_running_processes(self) -> List[Dict]:
        """Capture all running processes"""
        processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    info = proc.info
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'exe': info['exe'],
                        'cmdline': info['cmdline']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.error(f"Error capturando procesos: {e}")

        return processes

    def capture_current_state(self) -> Dict:
        """
        Capture complete current state: apps, windows, browser tabs.
        Returns a dictionary with all state information.
        """
        self.logger.info("Capturando estado actual del sistema...")

        state = {
            'timestamp': datetime.now().isoformat(),
            'processes': self._capture_running_processes(),
            'windows': self._capture_window_positions(),
            'browser_tabs': self._capture_browser_tabs()
        }

        self.logger.info(f"Estado capturado: {len(state['processes'])} procesos, "
                        f"{len(state['windows'])} ventanas, {len(state['browser_tabs'])} tabs")

        return state

    def restore_state(self, state: Dict):
        """
        Restore a previously saved state.
        Reopens apps, restores window positions, and browser tabs with exact URLs.
        """
        if not state:
            self.logger.warning("️ No hay estado para restaurar")
            return

        self.logger.info(f"Restoring estado del sistema ({state.get('timestamp', 'unknown')})")

        # 1. Restore processes (apps) - but DON'T restore system processes or browsers
        restored_apps = 0
        browser_exes = ['chrome.exe', 'brave.exe', 'msedge.exe', 'firefox.exe']

        # Use same protection list as _close_state_apps_and_tabs
        system_exes = [
            # Core Windows
            'explorer.exe', 'dwm.exe', 'csrss.exe', 'winlogon.exe', 'lsass.exe', 'services.exe',
            'smss.exe', 'wininit.exe', 'svchost.exe', 'spoolsv.exe', 'taskhostw.exe',
            # Shell and UI
            'sihost.exe', 'shellhost.exe', 'shellexperiencehost.exe', 'startmenuexperiencehost.exe',
            'searchhost.exe', 'searchindexer.exe', 'runtimebroker.exe', 'applicationframehost.exe',
            # Input and Display
            'ctfmon.exe', 'textinputhost.exe', 'tabtip.exe', 'osk.exe',
            # System Services
            'conhost.exe', 'dllhost.exe', 'fontdrvhost.exe', 'lsaiso.exe', 'lsm.exe',
            'msdtc.exe', 'sppsvc.exe', 'searchprotocolhost.exe', 'searchfilterhost.exe',
            # Security
            'securityhealthservice.exe', 'securityhealthsystray.exe', 'smartscreen.exe',
            'msmpeng.exe', 'nissrv.exe', 'antimalware service executable',
            # Windows Features
            'widgets.exe', 'widgetservice.exe', 'phoneexperiencehost.exe',
            'crossdeviceresume.exe', 'monotificationux.exe',
            # Audio/Video
            'audiodg.exe',
            # Drivers and Hardware
            'etdctrl.exe', 'amdrsserv.exe', 'radeonsoftware.exe', 'secocl64.exe',
            # Python (this app itself)
            'python.exe', 'pythonw.exe', 'py.exe',
            # Development tools
            'cmd.exe', 'powershell.exe', 'windowsterminal.exe', 'openconsole.exe',
            'cursor.exe', 'code.exe', 'devenv.exe', 'claude.exe',
            # Edge WebView
            'msedgewebview2.exe',
            # Windows Update
            'wuauclt.exe', 'trustedinstaller.exe', 'tiworker.exe',
            # Network
            'dashost.exe',
            # Other critical
            'figma_agent.exe', 'cncmd.exe', 'cpumetricsserver.exe'
        ]

        for proc_info in state.get('processes', []):
            try:
                process_name = proc_info.get('name', '').lower()
                if not process_name:
                    continue

                # Skip browsers (tabs are restored separately)
                if process_name in browser_exes:
                    continue

                # Skip system processes
                if process_name in system_exes:
                    continue

                # Check if already running
                is_running = False
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'].lower() == process_name:
                        is_running = True
                        break

                if not is_running:
                    exe_path = proc_info.get('exe')
                    if exe_path:
                        # Try to launch the app
                        try:
                            subprocess.Popen(exe_path)
                            restored_apps += 1
                            self.logger.info(f"Restaurado: {process_name}")
                        except Exception as e:
                            self.logger.warning(f"Could not restore {process_name}: {e}")

            except Exception as e:
                self.logger.warning(f"Error procesando app: {e}")

        # 2. Restore mode apps (apps from 'open' list that were closed during break)
        restored_mode_apps = 0
        mode_apps = state.get('mode_apps', [])
        if mode_apps and self.current_mode and self.modes.get(self.current_mode):
            mode_data = self.modes[self.current_mode]
            # Get full app configs from mode data
            apps_to_open = mode_data.get('open', [])

            for app_name in mode_apps:
                # Find the matching app config
                for app_config in apps_to_open:
                    if app_config.get('name') == app_name:
                        try:
                            # Check if app is already running (skip browsers - they stay open)
                            app_name_lower = app_name.lower()
                            is_browser = app_name_lower in ['chrome', 'brave', 'edge', 'firefox']

                            if is_browser:
                                self.logger.info(f"  ⏭️ Browser already open, skip: {app_name}")
                                restored_mode_apps += 1  # Count as restored
                                break

                            # Check if non-browser app is running
                            is_running = False
                            for proc in psutil.process_iter(['name']):
                                proc_name = proc.info['name'].lower()
                                if (app_name_lower in proc_name or
                                    proc_name.replace('.exe', '') in app_name_lower):
                                    is_running = True
                                    self.logger.info(f"  ⏭️ App already running, skip: {app_name} ({proc_name})")
                                    break

                            if is_running:
                                restored_mode_apps += 1  # Count as restored
                                break

                            # App not running, launch it
                            self.logger.info(f"  🚀 Lanzando app: {app_name}")
                            if self.launcher.launch_application(app_config):
                                restored_mode_apps += 1
                                self.logger.info(f"  ✅ Mode app restored: {app_name}")
                            else:
                                self.logger.warning(f"  ❌ Failed to launch app: {app_name}")
                        except Exception as e:
                            self.logger.warning(f"Error restoring mode app {app_name}: {e}")
                        break

        # 3. Restore browser tabs (wait for browser apps to launch first)
        restored_tabs = 0
        if BROWSER_CONTROL_AVAILABLE and state.get('browser_tabs'):
            # Wait 2 seconds for browser apps to launch and be ready
            # This is critical: browser must be running before we can restore tabs
            QTimer.singleShot(2000, lambda: self._restore_browser_tabs(state.get('browser_tabs', [])))
            restored_tabs = len(state.get('browser_tabs', []))
            self.logger.info(f"Scheduled restoration of {restored_tabs} tabs in 2 seconds...")

        # 4. Restore window positions (after a delay to let apps open)
        # We'll do this in a separate timer to allow apps to fully launch
        if WIN32_AVAILABLE and state.get('windows'):
            QTimer.singleShot(2000, lambda: self._restore_window_positions(state['windows']))

        self.logger.info(f"Restoration complete: {restored_apps} apps, {restored_mode_apps} mode apps, {restored_tabs} tabs")

    def _close_state_apps_and_tabs(self, state: Dict):
        """
        Close all apps and browser tabs from a saved state.
        Used whon transitioning betweon work/break phases.
        """
        if not state:
            return

        self.logger.info("️ Closing apps y tabs de la fase anterior...")

        # 1. Close browser tabs from the saved state
        closed_tabs = 0
        if BROWSER_CONTROL_AVAILABLE:
            state_tab_urls = set()
            for tab_info in state.get('browser_tabs', []):
                url = tab_info.get('url', '')
                if url:
                    # Store just the base URL without query params for matching
                    state_tab_urls.add(url.split('?')[0].split('#')[0])

            # Go through each browser and close tabs that match the state
            for port, controller in self.browser_controllers.items():
                try:
                    current_tabs = controller.get_open_tabs()

                    for tab in current_tabs:
                        tab_url = tab.get('url', '')
                        tab_id = tab.get('id', '')

                        if not tab_url or not tab_id:
                            continue

                        # Skip chrome:// and edge:// pages
                        if tab_url.startswith('chrome://') or tab_url.startswith('edge://') or tab_url.startswith('chrome-extension://'):
                            continue

                        # Check if this tab URL matches any from the saved state
                        base_url = tab_url.split('?')[0].split('#')[0]

                        for state_url in state_tab_urls:
                            if base_url.startswith(state_url[:50]) or state_url.startswith(base_url[:50]):
                                # This tab belongs to the old state - close it
                                # BUT: don't close if it's the last tab (would close browser)
                                if len(current_tabs) > 1:
                                    if controller.close_tab(tab_id):
                                        closed_tabs += 1
                                        self.logger.info(f"Tab cerrado: {tab_url[:50]}...")
                                else:
                                    # If it's the last tab, navigate to about:blank instead
                                    self.logger.info(f"Last tab - navigating to about:blank instead of closing")
                                    try:
                                        ws_url = tab.get('webSocketDebuggerUrl')
                                        if ws_url:
                                            import websocket
                                            import json as json_lib

                                            ws = websocket.create_connection(ws_url, timeout=1)
                                            nav_cmd = {
                                                "id": 1,
                                                "method": "Page.navigate",
                                                "params": {"url": "about:blank"}
                                            }
                                            ws.send(json_lib.dumps(nav_cmd))
                                            ws.close()
                                    except:
                                        pass
                                break

                except Exception as e:
                    self.logger.warning(f"Error cerrando tabs del puerto {port}: {e}")

        # 2. Close apps from the saved state (but keep system apps and browsers)
        closed_apps = 0
        browser_exes = ['chrome.exe', 'brave.exe', 'msedge.exe', 'firefox.exe']

        # Extended list of Windows system processes that should NEVER be closed
        system_exes = [
            # Core Windows
            'explorer.exe', 'dwm.exe', 'csrss.exe', 'winlogon.exe', 'lsass.exe', 'services.exe',
            'smss.exe', 'wininit.exe', 'svchost.exe', 'spoolsv.exe', 'taskhostw.exe',

            # Shell and UI
            'sihost.exe', 'shellhost.exe', 'shellexperiencehost.exe', 'startmenuexperiencehost.exe',
            'searchhost.exe', 'searchindexer.exe', 'runtimebroker.exe', 'applicationframehost.exe',

            # Input and Display
            'ctfmon.exe', 'textinputhost.exe', 'tabtip.exe', 'osk.exe',

            # System Services
            'conhost.exe', 'dllhost.exe', 'fontdrvhost.exe', 'lsaiso.exe', 'lsm.exe',
            'msdtc.exe', 'sppsvc.exe', 'searchprotocolhost.exe', 'searchfilterhost.exe',

            # Security
            'securityhealthservice.exe', 'securityhealthsystray.exe', 'smartscreen.exe',
            'msmpeng.exe', 'nissrv.exe', 'antimalware service executable',

            # Windows Features
            'widgets.exe', 'widgetservice.exe', 'phoneexperiencehost.exe',
            'crossdeviceresume.exe', 'monotificationux.exe',

            # Audio/Video
            'audiodg.exe',

            # Drivers and Hardware
            'etdctrl.exe', 'amdrsserv.exe', 'radeonsoftware.exe', 'secocl64.exe',

            # Python (this app itself)
            'python.exe', 'pythonw.exe', 'py.exe',

            # Development tools (keep IDE and terminal open)
            'cmd.exe', 'powershell.exe', 'windowsterminal.exe', 'openconsole.exe',
            'cursor.exe', 'code.exe', 'devenv.exe', 'claude.exe',

            # Edge WebView (used by many apps)
            'msedgewebview2.exe',

            # Windows Update and Maintenance
            'wuauclt.exe', 'trustedinstaller.exe', 'tiworker.exe',

            # Network
            'dashost.exe',

            # Other critical
            'figma_agent.exe', 'cncmd.exe', 'cpumetricsserver.exe'
        ]

        for proc_info in state.get('processes', []):
            try:
                process_name = proc_info.get('name', '').lower()

                if not process_name:
                    continue

                # Skip browsers (we handle tabs separately)
                if process_name in browser_exes:
                    continue

                # Skip system processes
                if process_name in system_exes:
                    continue

                # Check if process is still running
                for proc in psutil.process_iter(['name', 'pid']):
                    if proc.info['name'].lower() == process_name:
                        try:
                            # Close it
                            proc.terminate()
                            closed_apps += 1
                            self.logger.info(f"App cerrada: {process_name}")
                            break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

            except Exception as e:
                self.logger.warning(f"Error cerrando app: {e}")

        self.logger.info(f"️ Fase anterior cerrada: {closed_apps} apps, {closed_tabs} tabs")

    def _restore_tab_state(self, tab_info: Dict, port: int):
        """Restore scroll position and media time for a specific tab"""
        try:
            controller = self.browser_controllers.get(port)
            if not controller:
                return

            # Get the most recent tab (the one we just opened)
            tabs = controller.get_open_tabs()
            if not tabs:
                return

            # Find tab by URL (it should be the most recent one)
            target_url = tab_info.get('url', '')
            matching_tab = None
            for tab in tabs:
                if tab.get('url', '').startswith(target_url[:50]):  # Match first 50 chars
                    matching_tab = tab
                    break

            if not matching_tab:
                return

            ws_url = matching_tab.get('webSocketDebuggerUrl')
            if not ws_url:
                return

            import websocket
            import json as json_lib

            ws = websocket.create_connection(ws_url, timeout=2)

            # Restore scroll position
            if tab_info.get('scroll_x') is not None:
                scroll_x = tab_info.get('scroll_x', 0)
                scroll_y = tab_info.get('scroll_y', 0)

                scroll_script = f"window.scrollTo({scroll_x}, {scroll_y});"
                scroll_cmd = {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {"expression": scroll_script}
                }
                ws.send(json_lib.dumps(scroll_cmd))
                ws.recv()  # Wait for response
                self.logger.info(f"Scroll restored: ({scroll_x}, {scroll_y})")

            # Restore media time
            if tab_info.get('media_time') is not None:
                media_time = tab_info.get('media_time', 0)

                media_script = f"""
                (function() {{
                    var video = document.querySelector('video');
                    var audio = document.querySelector('audio');
                    var media = video || audio;
                    if (media) {{
                        media.currentTime = {media_time};
                        return true;
                    }}
                    return false;
                }})()
                """
                media_cmd = {
                    "id": 2,
                    "method": "Runtime.evaluate",
                    "params": {"expression": media_script}
                }
                ws.send(json_lib.dumps(media_cmd))
                response = ws.recv()
                result = json_lib.loads(response)

                if result.get('result', {}).get('result', {}).get('value'):
                    self.logger.info(f"Tiempo de video restaurado: {media_time:.1f}s")

            ws.close()

        except Exception as e:
            self.logger.warning(f"Could not restore estado detallado del tab: {e}")

    def _restore_window_positions(self, windows_state: List[Dict]):
        """Restore window positions after apps have launched"""
        restored = 0

        for window_info in windows_state:
            try:
                # Find window by title and process name
                target_title = window_info.get('title', '')
                target_process = window_info.get('process_name', '')

                if not target_title:
                    continue

                # Find matching window
                def find_window_callback(hwnd, result):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title == target_title:
                            result.append(hwnd)
                    return True

                found_windows = []
                win32gui.EnumWindows(find_window_callback, found_windows)

                if found_windows:
                    hwnd = found_windows[0]

                    # Restore position and size
                    x = window_info.get('x', 0)
                    y = window_info.get('y', 0)
                    width = window_info.get('width', 800)
                    height = window_info.get('height', 600)

                    win32gui.MoveWindow(hwnd, x, y, width, height, True)
                    restored += 1
                    self.logger.info(f"Position restored: {target_title[:40]}")

            except Exception as e:
                self.logger.warning(f"Error restoring window position: {e}")

        self.logger.info(f"{restored} posiciones de ventana restauradas")

    def monitor_blocked_apps(self):
        """
        Here I monitor blocked apps every 10 seconds.
        Si detecto que alguion abrió una app que debería estar cerrada, la cierro automáticamente.
        I ALSO monitor the whitelist if configured.
        """
        if not self.strict_monitor_active or not self.current_mode:
            return

        mode_data = self.modes.get(self.current_mode)
        if not mode_data:
            return

        # Monitoring is always active (independent of strict_mode)

        # 1. Check specifically blocked apps
        for app in self.blocked_apps:
            if self.process_manager.is_process_running(app):
                # The app is running whon it should NOT
                self.logger.warning(f"Monitor: Closing {app} (blocked by mode {mode_data['name']})")

                if self.process_manager.close_process(app):
                    # Show notification that I blocked the app
                    self.show_block_notification(app, mode_data['name'])

        # 2. Check whitelist (only if enabled)
        whitelist_enabled = mode_data.get('whitelist_enabled', False)
        allowed_apps = mode_data.get('allowed_apps', [])

        # In Ultra Focus, continuous whitelist monitoring to ONLY allow selected browser
        if is_ultra_focus_active(mode_data):
            ultra_settings = mode_data['ultra_focus_settings']

            # Only enable if close_all_non_browser_apps is checked
            if ultra_settings.get('close_all_non_browser_apps', False):
                selected_browser = ultra_settings.get('selected_browser', 'chrome')

                # Map browser name to executable
                browser_exe_map = {
                    'chrome': 'chrome.exe',
                    'brave': 'brave.exe',
                    'edge': 'msedge.exe'
                }

                allowed_apps = [browser_exe_map.get(selected_browser, 'chrome.exe')]

                # Also allow FocusManager.exe to prevent closing itself
                import sys
                if getattr(sys, 'frozen', False):
                    # Running as compiled executable
                    allowed_apps.append('FocusManager.exe')

                whitelist_enabled = True  # Force enable for Ultra Focus

        # Only apply whitelist monitoring if it's explicitly enabled
        if whitelist_enabled and allowed_apps:
            # Use ultra_strict for Ultra Focus mode
            ultra_strict_mode = is_ultra_focus_active(mode_data)
            # Protect launcher PID if running from python main.py
            additional_pids = [self.launcher_pid] if self.launcher_pid else None
            stats = self.process_manager.close_non_whitelisted_apps(allowed_apps, os.getpid(), additional_pids=additional_pids, ultra_strict=ultra_strict_mode)
            if stats['closed'] > 0:
                if ultra_strict_mode:
                    self.logger.warning(f"Ultra Focus: {stats['closed']} unauthorized apps closed automatically")
                else:
                    self.logger.warning(f"Whitelist: {stats['closed']} unauthorized apps closed automatically")

    def show_block_notification(self, app_name: str, mode_name: str):
        """Show a notification whon I block an app"""
        try:
            QMessageBox.warning(
                self,
                "🚫 App Bloqueada",
                f"{app_name} is blocked in mode {mode_name}.\n\n"
                f"Deactivate the mode if you want to use this application."
            )
        except:
            # Si hay error, solo logueo
            self.logger.info(f"Blocked: {app_name} in mode {mode_name}")

    def on_browser_block(self, url: str, title: str):
        """Callback cuando el Browser Controller bloquea un tab"""
        self.logger.warning(f"Browser: Tab bloqueado - {title} ({url})")

    def on_browser_closed_ultra_focus(self, port: int):
        """Callback when browser is closed during Focus or Ultra Focus mode - reopen it"""
        self.logger.info(f"DEBUG: on_browser_closed_ultra_focus called for port {port}")
        self.logger.info(f"DEBUG: current_mode = {self.current_mode}")

        # Check if we're in ANY active mode that uses browsers
        if not self.current_mode:
            self.logger.info(f"DEBUG: No active mode, ignoring browser closure")
            return  # No active mode, ignore

        # Check if it's Ultra Focus mode
        is_ultra_focus = hasattr(self, 'ultra_focus_active') and self.ultra_focus_active
        self.logger.info(f"DEBUG: is_ultra_focus = {is_ultra_focus}")

        if is_ultra_focus:
            self.logger.warning(f"⚠️ Ultra Focus: Browser closed! Reopening...")
        else:
            self.logger.warning(f"⚠️ Focus: Browser closed! Reopening...")

        # Get the browser configuration that was originally opened
        if not self.current_mode:
            return

        mode_data = self.modes.get(self.current_mode, {})
        apps_to_open = mode_data.get('open', [])
        ultra_settings = mode_data.get('ultra_focus_settings', {})
        locked_domain = ultra_settings.get('locked_domain', '')

        # Find the browser app configuration for this port
        from browser_focus.multi_browser import SUPPORTED_BROWSERS
        browser_name = None
        for bkey, bconfig in SUPPORTED_BROWSERS.items():
            if bconfig['port'] == port:
                browser_name = bkey
                break

        if not browser_name:
            return

        # Find the app config for this browser
        for app_config in apps_to_open:
            if app_config.get('name') == browser_name:
                # Clone app config to avoid modifying original
                reopened_config = app_config.copy()

                # Add locked domain as initial URL if specified
                if locked_domain:
                    url = f"https://{locked_domain}"
                    if 'args' not in reopened_config:
                        reopened_config['args'] = []
                    else:
                        reopened_config['args'] = reopened_config['args'].copy()

                    # Add URL as argument if not already there
                    if url not in reopened_config['args']:
                        reopened_config['args'].append(url)

                # Reopen the browser with debug args
                import time
                time.sleep(2)  # Wait a moment before reopening
                success = self.launcher.launch_application(reopened_config)

                if success:
                    if is_ultra_focus:
                        self.logger.info(f"✅ Browser {browser_name} reopened in debug mode on {locked_domain}")

                        # Wait for browser to start and then reactivate Ultra Focus
                        time.sleep(3)

                        # Reactivate Ultra Focus on the controller
                        if port in self.browser_integrations:
                            controller = self.browser_integrations[port].controller
                            controller.activate_ultra_focus_with_domain(ultra_settings, locked_domain)
                            self.logger.info(f"🔒 Ultra Focus re-activated on {browser_name}")
                    else:
                        # Focus mode: just reopen, no special Ultra Focus setup
                        self.logger.info(f"✅ Browser {browser_name} reopened in debug mode")
                else:
                    self.logger.error(f"❌ Failed to reopen browser {browser_name}")
                break

    def show_stats(self):
        """Show the window with all my usage statistics"""
        from stats_window import StatsWindow
        stats_win = StatsWindow(self, self.stats)
        stats_win.exec()

    def show_about(self):
        """Show About dialog with developer information"""
        about_dialog = AboutDialog(self)
        about_dialog.exec()

    def show_config(self):
        """Show window to configure modes and PIN"""
        # Create general configuration window
        dialog = QDialog(self)
        dialog.setWindowTitle(lang.get('config_title'))
        dialog.setMinimumSize(500, 550)

        layout = QVBoxLayout()

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #3498db; min-height: 60px;")
        header_layout = QVBoxLayout(header_frame)

        header_label = QLabel(f"{lang.get('config_title').upper()}")
        header_label.setFont(QFont('Arial', 14, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)

        layout.addWidget(header_frame)

        # General Configuration Section
        general_group = QGroupBox(lang.get('general_settings'))
        general_group.setFont(QFont('Arial', 11, QFont.Bold))
        general_layout = QVBoxLayout()

        # Selector de idioma
        lang_layout = QHBoxLayout()

        lang_label = QLabel(lang.get('language_label'))
        lang_label.setFont(QFont('Arial', 10))
        lang_layout.addWidget(lang_label)

        # ComboBox para idioma
        from PySide6.QtWidgets import QComboBox
        self.language_combo = QComboBox()
        self.language_combo.setFont(QFont('Arial', 10))
        self.language_combo.addItem(f"🇪🇸 {lang.get('spanish')}", "es")
        self.language_combo.addItem(f"🇬🇧 {lang.get('english')}", "en")

        # Seleccionar idioma actual
        current_lang = lang.get_current_language()
        if current_lang == 'es':
            self.language_combo.setCurrentIndex(0)
        else:
            self.language_combo.setCurrentIndex(1)

        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()

        general_layout.addLayout(lang_layout)

        # Mensaje de info sobre reinicio
        if lang.get_current_language() == 'es':
            info_text = "💡 The application will restart to apply the language change"
        else:
            info_text = "💡 The application will restart to apply the language change"

        lang_info = QLabel(info_text)
        lang_info.setFont(QFont('Arial', 9))
        lang_info.setStyleSheet("color: #7f8c8d; font-style: italic;")
        general_layout.addWidget(lang_info)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        # Parental PIN Section
        pin_group = QGroupBox(lang.get('pin_config'))
        pin_group.setFont(QFont('Arial', 11, QFont.Bold))
        pin_layout = QVBoxLayout()

        # Estado del PIN
        if self.pin_manager.has_pin():
            pin_status = QLabel(lang.get('pin_status_active'))
            pin_status.setStyleSheet("color: #3498db; font-weight: bold;")
        else:
            pin_status = QLabel(lang.get('pin_status_inactive'))
            pin_status.setStyleSheet("color: #95a5a6; font-weight: bold;")

        pin_status.setFont(QFont('Arial', 11))
        pin_status.setAlignment(Qt.AlignCenter)
        pin_layout.addWidget(pin_status)

        # Button to manage PIN
        if not self.pin_manager.has_pin():
            pin_action_btn = QPushButton(lang.get('activate_parental_pin'))
            pin_action_btn.setFont(QFont('Arial', 11, QFont.Bold))
            pin_action_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
            pin_action_btn.clicked.connect(lambda: self.setup_new_pin_from_config(dialog))
        else:
            pin_action_btn = QPushButton(lang.get('manage_pin'))
            pin_action_btn.setFont(QFont('Arial', 11))
            pin_action_btn.setMinimumHeight(40)
            pin_action_btn.clicked.connect(lambda: self.show_pin_config_from_config(dialog))

        pin_layout.addWidget(pin_action_btn)
        pin_group.setLayout(pin_layout)
        layout.addWidget(pin_group)

        # Modes Section
        modes_group = QGroupBox(lang.get('configure_modes'))
        modes_group.setFont(QFont('Arial', 11, QFont.Bold))
        modes_layout = QVBoxLayout()

        desc = QLabel(lang.get('select_mode_to_config'))
        desc.setFont(QFont('Arial', 10))
        desc.setStyleSheet("color: #7f8c8d;")
        modes_layout.addWidget(desc)

        # Scroll area for modes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for mode_id in self.modes.keys():
            if mode_id == 'TEMPLATE':
                continue

            mode_data = self.modes[mode_id]
            btn = QPushButton(mode_data.get('name', mode_id))
            btn.setFont(QFont('Arial', 10))
            btn.setMinimumHeight(60)

            # Set icon from SVG file
            icon_filename_map = {
                'focus': 'focus.svg',
                'ultra_focus': 'ultrafocus.svg',
            }

            icon_filename = icon_filename_map.get(mode_id)
            if icon_filename:
                icon_path = Path(__file__).parent / 'icons' / icon_filename
                if icon_path.exists():
                    from PySide6.QtGui import QIcon
                    from PySide6.QtCore import QSize
                    btn.setIcon(QIcon(str(icon_path)))
                    btn.setIconSize(QSize(24, 24))

            btn.clicked.connect(lambda checked, m=mode_id, d=dialog: self.open_mode_config(m, d))
            scroll_layout.addWidget(btn)

        scroll.setWidget(scroll_widget)
        modes_layout.addWidget(scroll)
        modes_group.setLayout(modes_layout)
        layout.addWidget(modes_group)

        dialog.setLayout(layout)
        dialog.exec()

    def open_mode_config(self, mode_id, parent_dialog):
        """Opon the configurator for a specific mode"""
        parent_dialog.accept()

        config_win = ConfigWindow(
            self,
            mode_id,
            self.modes[mode_id],
            on_save_callback=self.reload_modes
        )
        config_win.exec()

    def reload_modes(self):
        """Reload modes after saving config"""
        self.modes = self.load_modes()
        # Update UI - refresh mode buttons
        for mode_id, btn in self.mode_buttons.items():
            if mode_id in self.modes:
                mode_data = self.modes[mode_id]
                btn.setText(mode_data['name'])

        # Update status display if current mode was updated
        if self.current_mode and self.current_mode in self.modes:
            self.update_status_display()

    def setup_new_pin_from_config(self, parent_dialog):
        """Configure a new PIN from the configuration menu"""
        dialog = SetPINDialog(parent_dialog)
        result = dialog.show()

        if result:
            pin = result['pin']
            parental_mode = result['parental_mode']
            security_question = result.get('security_question')

            # Save PIN with security questions if provided (now mandatory)
            if security_question:
                questions_list = security_question.get('questions', [])
                if self.pin_manager.set_pin(pin, questions_list):
                    self.pin_manager.enable_parental_mode(parental_mode)
                    status = lang.get('parental_mode_on') if parental_mode else lang.get('parental_mode_off')
                    num_questions = len(questions_list)
                    QMessageBox.information(
                        self,
                        lang.get('pin_configured'),
                        lang.get('pin_configured_message', status=status) + f"\n\n{num_questions} preguntas de seguridad configuradas exitosamente." if lang.get_current_language() == 'es' else f"\n\n{num_questions} security questions configured successfully."
                    )
                    parent_dialog.accept()
                    # Reopen configuration to show the change
                    self.show_config()
                else:
                    error_msg = "No se pudo guardar el PIN" if lang.get_current_language() == 'es' else "Could not save PIN"
                    QMessageBox.critical(self, lang.get('error_no_pin'), error_msg)

    def show_pin_config_from_config(self, parent_dialog):
        """Show PIN management from configuration (requires verifying PIN first)"""
        if not self.verify_pin_access("gestionar PIN"):
            return

        parent_dialog.accept()
        self.show_pin_config(skip_verification=True)

    def on_language_changed(self, index):
        """Handle language change"""
        from translations import lang

        new_lang = self.language_combo.itemData(index)
        current_lang = lang.get_current_language()

        # If language didn't change, do nothing
        if new_lang == current_lang:
            return

        # Save the new language
        self.settings_manager.set_language(new_lang)

        # Show message that language will be applied on next restart
        msg = QMessageBox(self)
        if new_lang == 'es':
            msg.setWindowTitle("Idioma cambiado")
            msg.setText("El idioma se aplicará cuando reinicies la aplicación.")
        else:
            msg.setWindowTitle("Language changed")
            msg.setText("The language will be applied when you restart the application.")
        msg.setIcon(QMessageBox.Information)
        msg.exec()

    def verify_pin_access(self, action: str) -> bool:
        """Verify PIN before allowing a sensitive action"""
        if not self.pin_manager.is_pin_enabled():
            return True  # No hay PIN configurado, permitir

        dialog = PINDialog(
            self,
            title=lang.get('auth_required'),
            message=lang.get('enter_pin_for', action=action)
        )
        entered_pin = dialog.show()

        if entered_pin is None:
            return False  # User cancelled

        if self.pin_manager.verify_pin(entered_pin):
            return True
        else:
            access_denied = "Acceso denegado." if lang.get_current_language() == 'es' else "Access denied."
            QMessageBox.critical(
                self,
                lang.get('pin_incorrect'),
                f"{lang.get('pin_error')}\n{access_denied}"
            )
            return False

    # System Tray slot methods
    @Slot()
    def _show_from_tray(self):
        """Show window from system tray (Qt slot)"""
        self.show()
        self.raise_()
        self.activateWindow()

    @Slot()
    def _quit_with_pin_check(self):
        """Quit after PIN verification (Qt slot)"""
        if self.verify_pin_access("close the application"):
            if self.tray_icon:
                self.tray_icon.stop()
            QApplication.quit()

    @Slot()
    def _warn_active_mode_quit(self):
        """Warn about quitting with active mode (Qt slot)"""
        reply = QMessageBox.question(
            self,
            "Active Mode",
            f"You have an active mode ({self.current_mode}).\nAre you sure you want to quit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.tray_icon:
                self.tray_icon.stop()
            QApplication.quit()

    @Slot()
    def _safe_quit(self):
        """Safe quit with no active mode (Qt slot)"""
        if self.tray_icon:
            self.tray_icon.stop()
        QApplication.quit()

    def show_pin_config(self, skip_verification=False):
        """Show window to configure parental PIN"""
        # Si ya hay PIN, verificar primero (a menos que ya se verificó)
        if self.pin_manager.has_pin() and not skip_verification:
            if not self.verify_pin_access("change PIN configuration"):
                return

        # Options menu
        dialog = QDialog(self)
        dialog.setWindowTitle("PIN Configuration")
        dialog.setMinimumSize(450, 350)

        layout = QVBoxLayout()

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #3498db; min-height: 60px;")
        header_layout = QVBoxLayout(header_frame)

        header_label = QLabel("PARENTAL PIN CONFIGURATION")
        header_label.setFont(QFont('Arial', 14, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(header_label)

        layout.addWidget(header_frame)

        # Info with check icon if PIN is set
        info_text = "The parental PIN protects the application so that only\n" \
                    "you can deactivate modes or change settings."

        if self.pin_manager.has_pin():
            # Create horizontal layout for "PIN configurado" with check icon
            pin_status_layout = QHBoxLayout()
            pin_status_layout.addStretch()

            check_icon_path = Path(__file__).parent / 'icons' / 'check.svg'
            if check_icon_path.exists():
                from PySide6.QtSvgWidgets import QSvgWidget
                check_svg = QSvgWidget(str(check_icon_path))
                check_svg.setFixedSize(20, 20)
                pin_status_layout.addWidget(check_svg)

            pin_status_label = QLabel("PIN configurado")
            pin_status_label.setFont(QFont('Arial', 10, QFont.Bold))
            pin_status_label.setStyleSheet("color: #FDFDFD;")
            pin_status_layout.addWidget(pin_status_label)
            pin_status_layout.addStretch()

            status_widget = QWidget()
            status_widget.setLayout(pin_status_layout)
            layout.addWidget(status_widget)

        info_label = QLabel(info_text)
        info_label.setFont(QFont('Arial', 10))
        info_label.setStyleSheet("color: #7f8c8d;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # Botones
        if not self.pin_manager.has_pin():
            # Configurar nuevo PIN
            set_btn = QPushButton("Configurar PIN")
            set_btn.setFont(QFont('Arial', 11, QFont.Bold))
            set_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 50px;")
            set_btn.clicked.connect(lambda: self.setup_new_pin(dialog))
            layout.addWidget(set_btn)
        else:
            # Cambiar PIN
            change_btn = QPushButton("Cambiar PIN" if lang.get_current_language() == 'es' else "Change PIN")
            change_btn.setFont(QFont('Arial', 11))
            change_btn.setMinimumHeight(40)
            change_btn.clicked.connect(lambda: self.setup_new_pin(dialog))
            layout.addWidget(change_btn)

            # Cambiar Preguntas de Seguridad
            change_questions_btn = QPushButton("Cambiar Preguntas de Seguridad" if lang.get_current_language() == 'es' else "Change Security Questions")
            change_questions_btn.setFont(QFont('Arial', 11))
            change_questions_btn.setMinimumHeight(40)
            change_questions_btn.clicked.connect(lambda: self.change_security_questions(dialog))
            layout.addWidget(change_questions_btn)

            # Disable PIN
            remove_btn = QPushButton("Deshabilitar PIN" if lang.get_current_language() == 'es' else "Disable PIN")
            remove_btn.setFont(QFont('Arial', 11))
            remove_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
            remove_btn.clicked.connect(lambda: self.remove_pin(dialog))
            layout.addWidget(remove_btn)

        # Cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.setFont(QFont('Arial', 10))
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def setup_new_pin(self, parent_dialog):
        """Configuro un nuevo PIN"""
        dialog = SetPINDialog(parent_dialog)
        result = dialog.show()

        if result:
            pin = result['pin']
            parental_mode = result['parental_mode']
            security_question = result.get('security_question')

            # Save PIN with security questions (now mandatory)
            if security_question:
                questions_list = security_question.get('questions', [])
                if self.pin_manager.set_pin(pin, questions_list):
                    self.pin_manager.enable_parental_mode(parental_mode)
                    num_questions = len(questions_list)
                    QMessageBox.information(
                        self,
                        "PIN Configurado",
                        f"PIN configurado correctamente.\n\n"
                        f"Parental Mode: {'Enabled' if parental_mode else 'Disabled'}\n"
                        f"{num_questions} preguntas de seguridad configuradas exitosamente."
                    )
                    parent_dialog.accept()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo guardar el PIN")

    def change_security_questions(self, parent_dialog):
        """Change security questions without changing PIN"""
        from pin_dialog import SecurityQuestionDialog

        # Show security questions dialog
        security_dialog = SecurityQuestionDialog(parent_dialog)
        result = security_dialog.show()

        if result:
            questions_list = result.get('questions', [])
            if questions_list:
                # Get current config
                config = self.pin_manager.config

                # Update only security questions, keep PIN and parental mode
                hashed_questions = []
                for qa in questions_list:
                    hashed_questions.append({
                        'question': qa['question'],
                        'answer_hash': self.pin_manager.hash_pin(qa['answer'].lower().strip())
                    })

                config['security_questions'] = hashed_questions

                # Update compatibility fields
                if hashed_questions:
                    config['security_question'] = hashed_questions[0]['question']
                    config['security_answer_hash'] = hashed_questions[0]['answer_hash']

                # Save config
                if self.pin_manager.save_config():
                    num_questions = len(questions_list)
                    QMessageBox.information(
                        self,
                        "Preguntas Actualizadas" if lang.get_current_language() == 'es' else "Questions Updated",
                        f"Las preguntas de seguridad han sido actualizadas exitosamente.\n\n"
                        f"{num_questions} preguntas configuradas." if lang.get_current_language() == 'es'
                        else f"Security questions have been updated successfully.\n\n"
                        f"{num_questions} questions configured."
                    )
                    parent_dialog.accept()
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "No se pudo guardar las preguntas de seguridad" if lang.get_current_language() == 'es'
                        else "Could not save security questions"
                    )

    def remove_pin(self, parent_dialog):
        """Remove the PIN"""
        reply = QMessageBox.question(
            self,
            "Confirm",
            "Are you sure you want to disable the PIN?\n\n"
            "This will also disable parental mode.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.pin_manager.remove_pin()
            QMessageBox.information(self, "PIN Disabled", "The PIN has beon removed successfully")
            parent_dialog.accept()

    # ===== ULTRA FOCUS MODE =====

    def _activate_ultra_focus(self, mode_data: dict):
        """Activa Ultra Focus Mode con todas sus restricciones"""
        ultra_settings = mode_data.get('ultra_focus_settings', {})

        # Activate bloqueo de teclado
        if ultra_settings.get('block_all_shortcuts', True):
            from keyboard_blocker import KeyboardBlocker
            self.keyboard_blocker = KeyboardBlocker(
                logger=self.logger,
                on_block_callback=self._on_shortcut_blocked
            )
            self.keyboard_blocker.activate()
            self.logger.info(f"Bloqueo de atajos de teclado activado")

        # Determine domain to block
        use_current = ultra_settings.get('use_current_domain', False)
        locked_domain = ultra_settings.get('locked_domain', '')
        selected_browser = ultra_settings.get('selected_browser', 'chrome')

        # Map browser to port
        browser_port_map = {
            'chrome': (9222, "Chrome"),
            'brave': (9223, "Brave"),
            'edge': (9224, "Edge")
        }

        # Activate domain lockdown in selected browser
        domain_locked = False
        active_browser_port = None
        active_browser_name = None

        if selected_browser in browser_port_map:
            port, browser_name = browser_port_map[selected_browser]
            active_browser_port = port
            active_browser_name = browser_name

            # Verify that the browser is available
            if port in self.browser_controllers:
                controller = self.browser_controllers[port]

                if use_current:
                    # Use current browser domain
                    success = controller.activate_ultra_focus(ultra_settings)
                elif locked_domain:
                    # Use specified domain
                    success = controller.activate_ultra_focus_with_domain(ultra_settings, locked_domain)
                else:
                    # No hay dominio configurado
                    self.logger.warning("️ Ultra Focus activado sin dominio configurado")
                    success = False

                if success:
                    domain_locked = True
                    display_domain = controller.ultra_focus_locked_domain
                    self.logger.info(f"Ultra Focus activado on {browser_name} (puerto {port}) - Dominio: {display_domain}")
                else:
                    self.logger.error(f"❌ Could not activate Ultra Focus on {browser_name}")
            else:
                self.logger.error(f"❌ Navegador {browser_name} no disponible (puerto {port})")
        else:
            self.logger.error(f"❌ Invalid browser selected: {selected_browser}")

        # Second: Close the other 2 browsers
        if active_browser_port:
            import psutil
            browsers_to_close = []

            if active_browser_port != 9222:
                browsers_to_close.append(('chrome.exe', 'Chrome'))
            if active_browser_port != 9223:
                browsers_to_close.append(('brave.exe', 'Brave'))
            if active_browser_port != 9224:
                browsers_to_close.append(('msedge.exe', 'Edge'))
                # Note: msedgewebview2.exe is a system component, not a browser - don't close it

            for exe_name, browser_name in browsers_to_close:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] and proc.info['name'].lower() == exe_name.lower():
                            proc.terminate()
                            self.logger.info(f"Navegador cerrado (Ultra Focus): {browser_name} (PID {proc.info['pid']})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

            # Reduce monitoring interval to 0.5 seconds for Ultra Focus
            if active_browser_port in self.browser_monitors:
                monitor = self.browser_monitors[active_browser_port]
                monitor.interval = 0.5  # Aggressive monitoring every 0.5 seconds (500ms)
                self.logger.info(f"⚡ Accelerated monitoring to 0.5 seconds for Ultra Focus")

        # NOTE: Second close DISABLED - apps already closed in ModeActivationWorker
        # The continuous monitor will handle closing new apps every 5 seconds
        # This prevents the issue where py.exe gets closed

        # Mark as active
        self.ultra_focus_active = True
        self.ultra_focus_browser_port = active_browser_port
        self.ultra_focus_selected_browser = selected_browser  # Save selected browser
        self.ultra_focus_locked_domain = locked_domain if domain_locked else None
        # ultra_focus_main_pid already set in __init__, no need to set again

        # Start unauthorized browsers monitor (close normal chrome/brave/edge)
        from PySide6.QtCore import QTimer
        if not hasattr(self, 'unauthorized_browser_monitor'):
            self.unauthorized_browser_monitor = QTimer()
            self.unauthorized_browser_monitor.timeout.connect(self._close_unauthorized_browsers)
        self.unauthorized_browser_monitor.start(3000)  # Every 3 seconds

        # Save information to show message later
        close_all_apps = ultra_settings.get('close_all_non_browser_apps', False)

        # Start continuous monitoring for external apps if close_all_non_browser_apps is enabled
        if close_all_apps:
            if not hasattr(self, 'ultra_focus_apps_monitor'):
                self.ultra_focus_apps_monitor = QTimer()
                self.ultra_focus_apps_monitor.timeout.connect(self._close_non_browser_apps)
            self.ultra_focus_apps_monitor.start(5000)  # Every 5 seconds
            self.logger.info("🔒 Continuous monitoring for external apps activated")
        self._ultra_focus_display_info = {
            'domain_locked': domain_locked,
            'active_browser_name': active_browser_name,
            'locked_domain_display': locked_domain if domain_locked else None,
            'close_all_apps': close_all_apps
        }

        # Show notification AFTER browsers have beon closed
        QTimer.singleShot(2000, self._show_ultra_focus_message)  # 2 seconds later

    def _close_unauthorized_browsers(self):
        """Close browsers that are not debugging ones and reopon if authorized closes"""
        if not self.ultra_focus_active:
            return

        import psutil

        # PIDs de los browsers de debugging (para NO cerrarlos)
        debug_browser_pids = set()
        authorized_browser_running = False

        # Determine authorized browser process
        browser_exe_map = {
            'chrome': 'chrome.exe',
            'brave': 'brave.exe',
            'edge': 'msedge.exe'
        }

        authorized_browser_exe = browser_exe_map.get(
            getattr(self, 'ultra_focus_selected_browser', 'chrome'),
            'chrome.exe'
        )

        # Primera pasada: encontrar todos los procesos con --remote-debugging-port
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline_str = ' '.join(proc.info['cmdline']).lower()
                    # If it has --remote-debugging-port, it's a debugging browser
                    if '--remote-debugging-port' in cmdline_str:
                        debug_browser_pids.add(proc.info['pid'])

                        # Verify if it's the authorized browser
                        if proc.info['name'] and proc.info['name'].lower() == authorized_browser_exe.lower():
                            authorized_browser_running = True

                        # Also add child processes
                        try:
                            for child in proc.children(recursive=True):
                                debug_browser_pids.add(child.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # If authorized browser is NOT running, reopon it
        if not authorized_browser_running:
            self.logger.warning(f"⚠️ Authorized browser ({authorized_browser_exe}) not running - reopening...")
            self._reopen_authorized_browser()
            return  # Wait for next cycle to close unauthorized browsers

        # Second pass: close unauthorized browsers (without debugging)
        browsers_to_check = ['chrome.exe', 'brave.exe', 'msedge.exe']
        closed_count = 0

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() in browsers_to_check:
                    # If it's NOT a debugging process, close it
                    if proc.info['pid'] not in debug_browser_pids:
                        proc.terminate()
                        closed_count += 1
                        self.logger.warning(f"🚫 Navegador no autorizado cerrado: {proc.info['name']} (PID {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if closed_count > 0:
            self.logger.info(f"Total browsers no autorizados cerrados: {closed_count}")

    def _reopen_authorized_browser(self):
        """Reopon authorized browser with correct domain"""
        if not self.ultra_focus_active:
            return

        # Get selected browser
        selected_browser = getattr(self, 'ultra_focus_selected_browser', 'chrome')

        # Get app config from current mode
        if not self.current_mode or self.current_mode not in self.modes:
            return

        mode_data = self.modes[self.current_mode]
        apps_to_open = mode_data.get('open', [])

        # Search for browser app
        browser_app = None
        for app in apps_to_open:
            if app.get('name', '').lower() == selected_browser:
                browser_app = app
                break

        if not browser_app:
            self.logger.error(f"No configuration found for browser {selected_browser}")
            return

        # Opon browser
        self.logger.info(f"🔄 Reopening {selected_browser}...")

        # Use launcher.launch_application to properly expand environment variables
        success = self.launcher.launch_application(browser_app)

        if success:
            self.logger.info(f"✅ {selected_browser} reabierto exitosamente")

            # Wait for browser to be ready and thon opon the correct domain
            from PySide6.QtCore import QTimer
            if hasattr(self, 'ultra_focus_locked_domain') and self.ultra_focus_locked_domain:
                QTimer.singleShot(3000, self._restore_ultra_focus_domain)
        else:
            self.logger.error(f"❌ Error reabriendo {selected_browser}")

    def _restore_ultra_focus_domain(self):
        """Restore locked domain in Ultra Focus after reopening browser"""
        if not self.ultra_focus_active:
            return

        port = getattr(self, 'ultra_focus_browser_port', None)
        locked_domain = getattr(self, 'ultra_focus_locked_domain', None)

        if port and port in self.browser_controllers and locked_domain:
            controller = self.browser_controllers[port]
            self.logger.info(f"🔒 Restoring dominio bloqueado: {locked_domain}")

            # Opon tab with the domain
            success = controller.open_new_tab(f"https://{locked_domain}")
            if success:
                self.logger.info(f"✅ Dominio restaurado: {locked_domain}")
            else:
                self.logger.error(f"❌ Error restaurando dominio: {locked_domain}")

    def _close_non_browser_apps(self):
        """Close all non-browser applications while Ultra Focus is active"""
        if not self.ultra_focus_active:
            return

        # Get selected browser
        selected_browser = getattr(self, 'ultra_focus_selected_browser', 'chrome')

        # Map browser name to executable
        browser_exe_map = {
            'chrome': 'chrome.exe',
            'brave': 'brave.exe',
            'edge': 'msedge.exe'
        }

        allowed_apps = [browser_exe_map.get(selected_browser, 'chrome.exe')]

        # Also allow FocusManager.exe to prevent closing itself
        import sys
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            allowed_apps.append('FocusManager.exe')

        # Use ultra_strict mode to only close user apps with windows
        # Use saved main PID to protect all parent processes (cmd, py.exe, etc.)
        # Also protect launcher PID if running from python main.py
        try:
            additional_pids = [self.launcher_pid] if self.launcher_pid else None
            stats = self.process_manager.close_non_whitelisted_apps(allowed_apps, self.main_pid, additional_pids=additional_pids, ultra_strict=True)
            if stats['closed'] > 0:
                self.logger.info(f"🔒 Ultra Focus: Closed {stats['closed']} external application(s)")
        except Exception as e:
            self.logger.error(f"❌ Error closing non-browser apps: {e}")

    def _close_debug_browser(self, browser_name):
        """Close debug browser process when mode ends"""
        import psutil

        browser_exe_map = {
            'chrome': 'chrome.exe',
            'brave': 'brave.exe',
            'edge': 'msedge.exe'
        }

        browser_exe = browser_exe_map.get(browser_name)
        if not browser_exe:
            return

        # Close all instances of the debug browser
        closed_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == browser_exe.lower():
                    # Check if it has --remote-debugging-port (debug browser)
                    if proc.info['cmdline']:
                        cmdline_str = ' '.join(proc.info['cmdline']).lower()
                        if '--remote-debugging-port' in cmdline_str:
                            proc.terminate()
                            closed_count += 1
                            self.logger.info(f"🔓 Debug browser closed: {browser_exe} (PID {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if closed_count > 0:
            self.logger.info(f"🔓 Total debug browser instances closed: {closed_count}")

    def _show_ultra_focus_message(self):
        """Show Ultra Focus activated message after everything is configured"""
        if not hasattr(self, '_ultra_focus_display_info'):
            return

        info = self._ultra_focus_display_info
        domain_locked = info.get('domain_locked', False)
        active_browser_name = info.get('active_browser_name', '')
        locked_domain_display = info.get('locked_domain_display', '')
        close_all_apps = info.get('close_all_apps', False)

        # Build message based on configuration
        if domain_locked and active_browser_name:
            message = f"Locked to {locked_domain_display} on {active_browser_name}\n"
            if close_all_apps:
                message += "Only the browser is allowed. All other apps will be closed automatically.\n"
            message += "PIN required to exit. Focus mode active."

            QMessageBox.information(
                self,
                "Ultra Focus",
                message
            )
        else:
            message = "Ultra Focus activated.\n"
            if close_all_apps:
                message += "Only the browser is allowed. All other apps will be closed automatically.\n"
            message += "PIN required to exit."

            QMessageBox.information(
                self,
                "Ultra Focus",
                message
            )

    def _deactivate_ultra_focus(self):
        """Desactiva Ultra Focus Mode"""
        if not self.ultra_focus_active:
            return

        # IMPORTANT: Set ultra_focus_active to False FIRST
        # This prevents browser monitors from reopening browsers when we close them
        self.ultra_focus_active = False

        # Stop unauthorized browsers monitor
        if hasattr(self, 'unauthorized_browser_monitor') and self.unauthorized_browser_monitor:
            self.unauthorized_browser_monitor.stop()
            self.logger.info("🔓 Monitor de browsers no autorizados detenido")

        # Stop external apps monitor
        if hasattr(self, 'ultra_focus_apps_monitor') and self.ultra_focus_apps_monitor:
            self.ultra_focus_apps_monitor.stop()
            self.logger.info("🔓 Monitor de apps externas detenido")

        # Stop browser monitors BEFORE closing debug browsers
        # This prevents them from detecting closure and reopening the browser
        for port, monitor in self.browser_monitors.items():
            monitor.stop()
            self.logger.info(f"🔓 Browser monitor stopped (port {port})")

        # Deactivate keyboard blocking
        if self.keyboard_blocker:
            self.keyboard_blocker.deactivate()
            self.keyboard_blocker = None
            self.logger.info("🔓 Bloqueo de atajos de teclado desactivado")

        # Deactivate browser lockdown
        for port, controller in self.browser_controllers.items():
            controller.deactivate_ultra_focus()
            self.logger.info(f"🔓 Ultra Focus deactivated in browser (port {port})")

        # Close debug browsers when Ultra Focus ends
        self._close_debug_browsers_ultra_focus()

        self.logger.info("🔓 Ultra Focus Mode desactivado")

    def _close_debug_browsers_ultra_focus(self):
        """Close debug browsers when Ultra Focus is deactivated"""
        import psutil
        import time

        debug_browsers = ['chrome.exe', 'brave.exe', 'msedge.exe']
        closed_pids = []

        # Find all debug browser parent processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and proc.info['name'].lower() in debug_browsers:
                    # Check if it has --remote-debugging-port (debug browser)
                    if proc.info['cmdline']:
                        cmdline_str = ' '.join(proc.info['cmdline']).lower()
                        if '--remote-debugging-port' in cmdline_str:
                            # Found a debug browser parent process
                            try:
                                # Kill all children first
                                children = proc.children(recursive=True)
                                for child in children:
                                    try:
                                        child.kill()
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        pass

                                # Then kill the parent
                                proc.kill()
                                closed_pids.append((proc.info['name'], proc.info['pid']))
                                self.logger.info(f"🔓 Debug browser killed (Ultra Focus end): {proc.info['name']} (PID {proc.info['pid']})")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if closed_pids:
            self.logger.info(f"🔓 Total debug browsers closed (Ultra Focus): {len(closed_pids)}")
            # Wait a moment to ensure browsers are fully closed
            time.sleep(0.5)

    def _on_shortcut_blocked(self, shortcut: str):
        """Callback cuando se bloquea un atajo on Ultra Focus"""
        # Log del intento
        settings = self.modes.get(self.current_mode, {}).get('ultra_focus_settings', {})
        if settings.get('log_escape_attempts', True):
            self.logger.warning(f"🚫 Intento de escape bloqueado: {shortcut}")

    def closeEvent(self, event):
        """Make sure to save everything before closing the app"""

        # Check if PIN is required (Ultra Focus or parental mode)
        ultra_focus_active = hasattr(self, 'ultra_focus_active') and self.ultra_focus_active
        parental_mode_active = self.pin_manager.is_parental_mode()

        # Request PIN only once if either condition requires it
        if ultra_focus_active or parental_mode_active:
            action = "close the application on Ultra Focus Mode" if ultra_focus_active else "close the application"
            if not self.verify_pin_access(action):
                event.ignore()
                if ultra_focus_active:
                    QMessageBox.warning(
                        self,
                        "Blocked",
                        "You cannot close the application while Ultra Focus Mode is active.\n\n"
                        "You must deactivate the mode first or enter the PIN."
                    )
                return

        if self.current_mode:
            reply = QMessageBox.question(
                self,
                "Confirm salida",
                "There is an active mode. Do you want to exit anyway?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Get current mode info BEFORE deactivating
                mode_name = self.modes[self.current_mode]['name']
                session_id = self.current_session_id

                # Close session WITHOUT logging MODE_DEACTIVATED (forced closure)
                if session_id:
                    self.stats.end_session(session_id)

                # Log application closure WITH mode active
                closure_method = "with PIN" if pin_required else "without PIN (no restrictions)"
                self.stats.log_application_closure_with_active_mode(closure_method, mode_name, session_id)

                # Deactivate UI elements silently (no logging, no session end)
                self.strict_monitor_active = False
                self.blocked_apps = []
                if hasattr(self, 'monitor_timer'):
                    self.monitor_timer.stop()

                self.timer_active = False
                self.timer_minutes_left = 0
                self.timer_mode_id = None
                if hasattr(self, 'countdown_timer'):
                    self.countdown_timer.stop()

                # Deactivate browsers silently
                if self.browser_integrations:
                    for integration in self.browser_integrations.values():
                        try:
                            integration.deactivate()
                        except:
                            pass

                if self.tray_icon:
                    self.tray_icon.stop()
                event.accept()
            else:
                event.ignore()
        else:
            # No active mode, just log the closure
            closure_method = "with PIN" if pin_required else "without PIN (no restrictions)"
            self.stats.log_application_closure(closure_method)

            if self.tray_icon:
                self.tray_icon.stop()
            event.accept()


if __name__ == '__main__':
    # When running gui.py directly, protect this process from being closed
    import os
    launcher_pid = os.getpid()

    app = QApplication(sys.argv)
    window = FocusManagerGUI(launcher_pid=launcher_pid)
    window.show()
    sys.exit(app.exec())
