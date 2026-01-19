"""
Visual configuration window for modes.
Configure which apps to close/open without editing JSON.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTabWidget, QWidget, QGroupBox, QScrollArea, QMessageBox, QFileDialog,
    QGridLayout, QRadioButton, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtSvgWidgets import QSvgWidget
import json
from pathlib import Path
from launcher import ApplicationLauncher
from browser_focus import BrowserDetector, SUPPORTED_BROWSERS
from translations import lang


class ConfigWindow(QDialog):
    """Window to configure modes visually"""

    def __init__(self, parent, mode_id, mode_data, on_save_callback):
        super().__init__(parent)
        self.mode_id = mode_id
        self.mode_data = mode_data.copy()
        self.on_save = on_save_callback

        # Create window
        self.setWindowTitle(lang.get('config_mode_title', mode=mode_data.get('name', mode_id)))
        self.setMinimumSize(600, 500)
        self.resize(800, 700)

        # Set window icon
        icon_path = Path(__file__).parent / 'icons' / 'logo.svg'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Search for common apps
        self.launcher = ApplicationLauncher()
        self.common_apps = self.launcher.find_common_applications()

        # Selected apps data
        self.selected_close_apps = set(self.mode_data.get('close', []))
        self.selected_open_apps = {}  # {nombre: {'path': str, 'args': list}}
        self.selected_allowed_apps = set(self.mode_data.get('allowed_apps', []))  # Whitelist

        # Initialize ultra_focus_check and whitelist_enabled_check to None (will be created later if needed)
        self.ultra_focus_check = None
        self.whitelist_enabled_check = None
        for app in self.mode_data.get('open', []):
            # Get name, if empty use file name
            app_name = app.get('name', '').strip()
            if not app_name:
                # Extract name from path
                app_path = app.get('path', '')
                if app_path:
                    app_name = Path(app_path).stem  # name without extension
                else:
                    app_name = 'App sin nombre'

            self.selected_open_apps[app_name] = {
                'path': app.get('path', ''),
                'args': app.get('args', [])
            }

        # Create interface
        self.create_widgets()

    def create_widgets(self):
        """Create all window elements"""

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2c3e50; min-height: 40px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)

        # Logo SVG
        logo_path = Path(__file__).parent / 'icons' / 'logo.svg'
        if logo_path.exists():
            logo_svg = QSvgWidget(str(logo_path))
            logo_svg.setFixedSize(28, 28)
            header_layout.addWidget(logo_svg)

        # Remove emoji from header and make text white
        mode_name = self.mode_data.get('name', '').upper()
        header_label = QLabel(f"CONFIGURAR MODO: {mode_name}" if lang.get_current_language() == 'es' else f"CONFIGURE MODE: {mode_name}")
        header_label.setFont(QFont('Arial', 12, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Notebook for tabs
        self.tabs = QTabWidget()

        # Ultra Focus: Only show general configuration
        if self.mode_id == 'ultra_focus':
            # Only configuration tab for Ultra Focus
            general_widget = QWidget()
            self.create_general_tab(general_widget)
            self.tabs.addTab(general_widget, "Configuration")
        else:
            # Normal modes: show all tabs
            # Tab 1: Apps (cerrar y abrir combinadas)
            apps_widget = QWidget()
            self.create_apps_tab(apps_widget)
            self.tabs.addTab(apps_widget, lang.get('apps_tab'))

            # Tab 2: Navegadores Web
            browsers_widget = QWidget()
            self.create_browsers_tab(browsers_widget)
            self.tabs.addTab(browsers_widget, lang.get('browsers_tab'))

            # Tab 3: General
            general_widget = QWidget()
            self.create_general_tab(general_widget)
            self.tabs.addTab(general_widget, lang.get('config_tab'))

        layout.addWidget(self.tabs)

        # Action buttons
        save_text = "GUARDAR CAMBIOS" if lang.get_current_language() == 'es' else "SAVE CHANGES"
        save_btn = QPushButton(save_text)
        save_btn.setFont(QFont('Arial', 11, QFont.Bold))
        save_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 50px;")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def create_apps_tab(self, parent):
        """Combined tab for apps to close and open"""

        main_layout = QHBoxLayout(parent)

        # ===== LEFT COLUMN: Apps to Close =====
        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)

        # Title outside container
        title_text = "APPS A CERRAR" if lang.get_current_language() == 'es' else "APPS TO CLOSE"
        title_close = QLabel(title_text)
        title_close.setFont(QFont('Arial', 11, QFont.Bold))
        title_close.setStyleSheet("color: white;")
        title_close.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title_close)

        # Remove emoji and reduce button size
        add_text = "Agregar app" if lang.get_current_language() == 'es' else "Add app"
        add_close_btn = QPushButton(add_text)
        add_close_btn.setFont(QFont('Arial', 10, QFont.Bold))
        add_close_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 35px; max-width: 150px;")
        add_close_btn.clicked.connect(self.add_close_app_manual)

        # Center button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(add_close_btn)
        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)

        # List of apps to close - Container with blue border
        self.close_scroll = QScrollArea()
        self.close_scroll.setWidgetResizable(True)
        self.close_scroll.setStyleSheet("QScrollArea { border: 1px solid #3498db; border-radius: 3px; background-color: #1e1e1e; }")
        self.close_list_widget = QWidget()
        self.close_list_layout = QVBoxLayout(self.close_list_widget)
        self.close_scroll.setWidget(self.close_list_widget)

        left_layout.addWidget(self.close_scroll)

        main_layout.addWidget(self.left_widget)

        # ===== RIGHT COLUMN: Apps to Open =====
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)

        # Title outside container
        title_text = "APPS A ABRIR" if lang.get_current_language() == 'es' else "APPS TO OPEN"
        title_open = QLabel(title_text)
        title_open.setFont(QFont('Arial', 11, QFont.Bold))
        title_open.setStyleSheet("color: white;")
        title_open.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title_open)

        # Remove emoji and reduce button size
        add_text = "Agregar app" if lang.get_current_language() == 'es' else "Add app"
        add_open_btn = QPushButton(add_text)
        add_open_btn.setFont(QFont('Arial', 10, QFont.Bold))
        add_open_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 35px; max-width: 150px;")
        add_open_btn.clicked.connect(self.add_open_app_manual)

        # Center button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(add_open_btn)
        btn_layout.addStretch()
        right_layout.addLayout(btn_layout)

        # List of apps to open - Container with blue border
        self.open_scroll = QScrollArea()
        self.open_scroll.setWidgetResizable(True)
        self.open_scroll.setStyleSheet("QScrollArea { border: 1px solid #3498db; border-radius: 3px; background-color: #1e1e1e; }")
        self.open_list_widget = QWidget()
        self.open_list_layout = QVBoxLayout(self.open_list_widget)
        self.open_scroll.setWidget(self.open_list_widget)

        right_layout.addWidget(self.open_scroll)

        main_layout.addWidget(self.right_widget)

        # ===== CENTER COLUMN: Allowed Apps (Whitelist) =====
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        # Title outside container
        title_text = "APPS PERMITIDAS (WHITELIST)" if lang.get_current_language() == 'es' else "ALLOWED APPS (WHITELIST)"
        title_allowed = QLabel(title_text)
        title_allowed.setFont(QFont('Arial', 11, QFont.Bold))
        title_allowed.setStyleSheet("color: white;")
        title_allowed.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(title_allowed)

        # Checkbox to enable/disable whitelist mode
        enable_text = "Activar modo whitelist (solo permitir estas apps)" if lang.get_current_language() == 'es' else "Enable whitelist mode (only allow these apps)"
        self.whitelist_enabled_check = QCheckBox(enable_text)
        self.whitelist_enabled_check.setFont(QFont('Arial', 9, QFont.Bold))
        self.whitelist_enabled_check.setStyleSheet("color: #3498db; margin: 5px;")
        self.whitelist_enabled_check.setChecked(self.mode_data.get('whitelist_enabled', False))
        self.whitelist_enabled_check.stateChanged.connect(self.toggle_whitelist_widgets)
        center_layout.addWidget(self.whitelist_enabled_check)

        # Description
        desc_text = "Cuando está activado, SOLO estas apps estarán permitidas (cierra todo lo demás)" if lang.get_current_language() == 'es' else "When enabled, ONLY these apps will be allowed (closes everything else)"
        whitelist_desc = QLabel(desc_text)
        whitelist_desc.setFont(QFont('Arial', 8))
        whitelist_desc.setStyleSheet("color: #FFFFFF; margin: 5px;")
        whitelist_desc.setWordWrap(True)
        center_layout.addWidget(whitelist_desc)

        # Remove emoji and reduce button size
        add_text = "Agregar app" if lang.get_current_language() == 'es' else "Add app"
        self.add_allowed_btn = QPushButton(add_text)
        self.add_allowed_btn.setFont(QFont('Arial', 10, QFont.Bold))
        self.add_allowed_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 35px; max-width: 150px;")
        self.add_allowed_btn.clicked.connect(self.add_allowed_app_manual)

        # Center button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.add_allowed_btn)
        btn_layout.addStretch()
        center_layout.addLayout(btn_layout)

        # List of allowed apps - Container with blue border
        self.allowed_scroll = QScrollArea()
        self.allowed_scroll.setWidgetResizable(True)
        self.allowed_scroll.setStyleSheet("QScrollArea { border: 1px solid #3498db; border-radius: 3px; background-color: #1e1e1e; }")
        self.allowed_list_widget = QWidget()
        self.allowed_list_layout = QVBoxLayout(self.allowed_list_widget)
        self.allowed_scroll.setWidget(self.allowed_list_widget)

        center_layout.addWidget(self.allowed_scroll)

        main_layout.addWidget(center_widget)

        # Initialize visibility based on checkbox state
        self.toggle_whitelist_widgets()

        # Refresh lists
        self.refresh_close_list()
        self.refresh_open_list()
        self.refresh_allowed_list()

    def create_browsers_tab(self, parent):
        """Tab to configure browsers and websites"""

        layout = QVBoxLayout(parent)

        # Scroll for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Title and description
        title = QLabel(lang.get('browser_control_title'))
        title.setFont(QFont('Arial', 14, QFont.Bold))
        title.setStyleSheet("color: #3498db;")
        title.setAlignment(Qt.AlignCenter)
        scroll_layout.addWidget(title)

        desc = QLabel(lang.get('browser_control_desc'))
        desc.setFont(QFont('Arial', 9))
        desc.setStyleSheet("color: #7f8c8d;")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        scroll_layout.addWidget(desc)

        # === SECTION: Add Browsers ===
        browsers_group = QGroupBox(lang.get('available_browsers'))
        browsers_group.setFont(QFont('Arial', 10, QFont.Bold))
        browsers_layout = QVBoxLayout()

        browsers_desc = QLabel(lang.get('available_browsers_desc'))
        browsers_desc.setFont(QFont('Arial', 9))
        browsers_desc.setStyleSheet("color: #7f8c8d;")
        browsers_desc.setWordWrap(True)
        browsers_layout.addWidget(browsers_desc)

        # Browser buttons
        buttons_layout = QHBoxLayout()

        # Detect installed browsers
        detected = BrowserDetector.find_all_browsers()

        # Create buttons for each supported browser
        for browser_key in ['chrome', 'brave', 'edge']:
            config = SUPPORTED_BROWSERS[browser_key]
            is_installed = browser_key in detected

            btn = QPushButton(lang.get('add_browser', browser=config['name']))
            btn.setFont(QFont('Arial', 10, QFont.Bold))
            btn.setMinimumHeight(50)

            if is_installed:
                btn.setStyleSheet("background-color: #3498db; color: white;")
                btn.clicked.connect(lambda checked, bk=browser_key: self.add_browser_configured(bk))
            else:
                btn.setStyleSheet("background-color: #bdc3c7; color: white;")
                btn.setEnabled(False)

            buttons_layout.addWidget(btn)

        browsers_layout.addLayout(buttons_layout)
        browsers_group.setLayout(browsers_layout)
        scroll_layout.addWidget(browsers_group)

        # === SECTION: List of Added Browsers ===
        self.browsers_list_group = QGroupBox(lang.get('configured_browsers'))
        self.browsers_list_group.setFont(QFont('Arial', 10, QFont.Bold))
        browsers_list_layout = QVBoxLayout()

        self.browsers_scroll = QScrollArea()
        self.browsers_scroll.setWidgetResizable(True)
        self.browsers_scroll.setMinimumHeight(150)
        self.browsers_list_widget = QWidget()
        self.browsers_list_layout = QVBoxLayout(self.browsers_list_widget)
        self.browsers_scroll.setWidget(self.browsers_list_widget)

        browsers_list_layout.addWidget(self.browsers_scroll)
        self.browsers_list_group.setLayout(browsers_list_layout)
        scroll_layout.addWidget(self.browsers_list_group)

        # === SECTION: Allowed Websites ===
        whitelist_group = QGroupBox(lang.get('allowed_websites'))
        whitelist_group.setFont(QFont('Arial', 10, QFont.Bold))
        whitelist_layout = QVBoxLayout()

        whitelist_desc = QLabel(lang.get('allowed_websites_desc'))
        whitelist_desc.setFont(QFont('Arial', 9))
        whitelist_desc.setStyleSheet("color: #7f8c8d;")
        whitelist_desc.setWordWrap(True)
        whitelist_layout.addWidget(whitelist_desc)

        whitelist_btn = QPushButton(lang.get('configure_allowed_websites'))
        whitelist_btn.setFont(QFont('Arial', 10, QFont.Bold))
        whitelist_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        whitelist_btn.clicked.connect(self.open_browser_whitelist)
        whitelist_layout.addWidget(whitelist_btn)

        whitelist_group.setLayout(whitelist_layout)
        scroll_layout.addWidget(whitelist_group)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Refrescar lista de navegadores
        self.refresh_browsers_list()

    def create_general_tab(self, parent):
        """Tab for general mode configuration"""

        layout = QVBoxLayout(parent)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Mode name
        name_group = QGroupBox(lang.get('mode_name'))
        name_group.setFont(QFont('Arial', 10, QFont.Bold))
        name_layout = QVBoxLayout()

        from PySide6.QtWidgets import QLineEdit
        self.name_entry = QLineEdit()
        self.name_entry.setFont(QFont('Arial', 11))
        self.name_entry.setText(self.mode_data.get('name', ''))
        name_layout.addWidget(self.name_entry)

        name_group.setLayout(name_layout)
        scroll_layout.addWidget(name_group)

        # Strict Mode
        strict_group = QGroupBox(lang.get('strict_mode_lock'))
        strict_group.setFont(QFont('Arial', 10, QFont.Bold))
        strict_layout = QVBoxLayout()

        from PySide6.QtWidgets import QCheckBox
        self.strict_mode_check = QCheckBox(lang.get('strict_mode_checkbox'))
        self.strict_mode_check.setFont(QFont('Arial', 10))
        self.strict_mode_check.setChecked(self.mode_data.get('strict_mode', False))
        strict_layout.addWidget(self.strict_mode_check)

        explanation = QLabel(lang.get('strict_mode_explanation'))
        explanation.setFont(QFont('Arial', 9))
        explanation.setStyleSheet("color: #7f8c8d;")
        strict_layout.addWidget(explanation)

        strict_group.setLayout(strict_layout)
        scroll_layout.addWidget(strict_group)

        # Ultra Focus Mode - Only show configuration if NOT normal Focus mode
        # Para el modo "ultra_focus", este ES el modo, no una opción
        if self.mode_id != 'ultra_focus':
            # In normal Focus mode: show as option with checkbox
            ultra_group = QGroupBox(lang.get('ultra_focus_lock'))
            ultra_group.setFont(QFont('Arial', 10, QFont.Bold))
            ultra_layout = QVBoxLayout()

            self.ultra_focus_check = QCheckBox(lang.get('ultra_focus_checkbox'))
            self.ultra_focus_check.setFont(QFont('Arial', 10))
            self.ultra_focus_check.setChecked(self.mode_data.get('ultra_focus_mode', False))
            ultra_layout.addWidget(self.ultra_focus_check)

            ultra_explanation = QLabel(lang.get('ultra_focus_explanation'))
            ultra_explanation.setFont(QFont('Arial', 9))
            ultra_explanation.setStyleSheet("color: #7f8c8d;")
            ultra_explanation.setWordWrap(True)
            ultra_layout.addWidget(ultra_explanation)

            # Separador
            ultra_layout.addSpacing(10)
        else:
            # In Ultra Focus mode: only show configuration directly
            ultra_group = QGroupBox(lang.get('ultra_focus_config_title'))
            ultra_group.setFont(QFont('Arial', 10, QFont.Bold))
            ultra_layout = QVBoxLayout()

            ultra_explanation = QLabel(lang.get('ultra_focus_config_subtitle'))
            ultra_explanation.setFont(QFont('Arial', 9))
            ultra_explanation.setStyleSheet("color: #7f8c8d;")
            ultra_explanation.setWordWrap(True)
            ultra_layout.addWidget(ultra_explanation)

            # Separador
            ultra_layout.addSpacing(10)

            # No checkbox because this mode is ALWAYS Ultra Focus
            self.ultra_focus_check = None

        # Domain configuration
        ultra_settings = self.mode_data.get('ultra_focus_settings', {})

        domain_label = QLabel(lang.get('ultra_domain_config'))
        domain_label.setFont(QFont('Arial', 9, QFont.Bold))
        ultra_layout.addWidget(domain_label)

        # If NOT ultra_focus mode, show radio buttons
        if self.mode_id != 'ultra_focus':
            # Radio: Use current domain
            self.ultra_use_current = QRadioButton(lang.get('ultra_use_current_domain'))
            self.ultra_use_current.setFont(QFont('Arial', 9))
            self.ultra_use_current.setChecked(ultra_settings.get('use_current_domain', False))
            ultra_layout.addWidget(self.ultra_use_current)

            # Radio: Specify domain
            self.ultra_specify_domain = QRadioButton(lang.get('ultra_specify_domain'))
            self.ultra_specify_domain.setFont(QFont('Arial', 9))
            self.ultra_specify_domain.setChecked(not ultra_settings.get('use_current_domain', False))
            ultra_layout.addWidget(self.ultra_specify_domain)

        # Text field + capture button
        domain_input_layout = QHBoxLayout()
        if self.mode_id != 'ultra_focus':
            domain_input_layout.setContentsMargins(20, 0, 0, 0)  # Indent only if there are radio buttons

        self.ultra_domain_input = QLineEdit()
        self.ultra_domain_input.setFont(QFont('Arial', 9))
        self.ultra_domain_input.setPlaceholderText("ejemplo: canvas.instructure.com")
        self.ultra_domain_input.setText(ultra_settings.get('locked_domain', ''))
        # In ultra_focus mode, always enabled. In focus mode, depends on radio
        if self.mode_id == 'ultra_focus':
            self.ultra_domain_input.setEnabled(True)
        else:
            self.ultra_domain_input.setEnabled(not ultra_settings.get('use_current_domain', False))
        domain_input_layout.addWidget(self.ultra_domain_input)

        self.ultra_capture_btn = QPushButton(lang.get('ultra_capture_current'))
        self.ultra_capture_btn.setFont(QFont('Arial', 9))
        if self.mode_id == 'ultra_focus':
            self.ultra_capture_btn.setEnabled(True)
        else:
            self.ultra_capture_btn.setEnabled(not ultra_settings.get('use_current_domain', False))
        self.ultra_capture_btn.clicked.connect(self.capture_current_domain)
        domain_input_layout.addWidget(self.ultra_capture_btn)

        ultra_layout.addLayout(domain_input_layout)

        # Connect radio buttons to enable/disable field (only if they exist)
        if self.mode_id != 'ultra_focus':
            self.ultra_use_current.toggled.connect(self.on_ultra_domain_mode_changed)

        # Separador
        ultra_layout.addSpacing(10)

        # Browser selector
        browser_label = QLabel(lang.get('ultra_browser_select'))
        browser_label.setFont(QFont('Arial', 9, QFont.Bold))
        ultra_layout.addWidget(browser_label)

        # ComboBox for browser
        from PySide6.QtWidgets import QComboBox
        self.ultra_browser_combo = QComboBox()
        self.ultra_browser_combo.setFont(QFont('Arial', 9))
        self.ultra_browser_combo.addItem("Chrome", "chrome")
        self.ultra_browser_combo.addItem("Brave", "brave")
        self.ultra_browser_combo.addItem("Edge", "edge")

        # Select saved browser
        selected_browser = ultra_settings.get('selected_browser', 'chrome')
        index = self.ultra_browser_combo.findData(selected_browser)
        if index >= 0:
            self.ultra_browser_combo.setCurrentIndex(index)

        ultra_layout.addWidget(self.ultra_browser_combo)

        # Explanation
        browser_explanation = QLabel(lang.get('ultra_browser_explanation'))
        browser_explanation.setFont(QFont('Arial', 8))
        browser_explanation.setStyleSheet("color: #95a5a6;")
        browser_explanation.setWordWrap(True)
        ultra_layout.addWidget(browser_explanation)

        # Separator
        ultra_layout.addSpacing(10)

        # Checkbox: Close all non-browser apps
        close_apps_text = "Cerrar todas las aplicaciones excepto el navegador" if lang.get_current_language() == 'es' else "Close all applications except the browser"
        self.ultra_close_apps_check = QCheckBox(close_apps_text)
        self.ultra_close_apps_check.setFont(QFont('Arial', 9, QFont.Bold))
        self.ultra_close_apps_check.setStyleSheet("color: #3498db;")
        self.ultra_close_apps_check.setChecked(ultra_settings.get('close_all_non_browser_apps', False))
        ultra_layout.addWidget(self.ultra_close_apps_check)

        close_apps_explanation = QLabel("Recomendado para máxima concentración" if lang.get_current_language() == 'es' else "Recommended for maximum concentration")
        close_apps_explanation.setFont(QFont('Arial', 8))
        close_apps_explanation.setStyleSheet("color: #95a5a6; margin-left: 20px;")
        close_apps_explanation.setWordWrap(True)
        ultra_layout.addWidget(close_apps_explanation)

        ultra_group.setLayout(ultra_layout)

        # Only add Ultra Focus config if it's Ultra Focus mode
        if self.mode_id == 'ultra_focus':
            scroll_layout.addWidget(ultra_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def add_to_close_list(self, exe_name):
        """Add an app to the close list"""
        self.selected_close_apps.add(exe_name)
        self.refresh_close_list()

    def remove_from_close_list(self, exe_name):
        """Remove an app from the close list"""
        self.selected_close_apps.discard(exe_name)
        self.refresh_close_list()

    def refresh_close_list(self):
        """Refresh visual list of apps to close"""
        # Limpiar
        while self.close_list_layout.count():
            child = self.close_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Agregar cada app seleccionada
        for exe_name in sorted(self.selected_close_apps):
            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #1e1e1e; border: none; border-radius: 3px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)

            display_text = str(exe_name).strip() if exe_name else '[Sin nombre]'
            if not display_text:
                display_text = '[App sin nombre]'

            label = QLabel(display_text)
            label.setFont(QFont('Arial', 10))
            label.setMinimumWidth(100)
            label.setStyleSheet("color: white; background: transparent;")
            item_layout.addWidget(label)

            item_layout.addStretch()

            remove_btn = QPushButton("✕")
            remove_btn.setFont(QFont('Arial', 12, QFont.Bold))
            remove_btn.setStyleSheet("background-color: #1e1e1e; color: #3498db; border: none; min-width: 40px; min-height: 30px;")
            remove_btn.clicked.connect(lambda checked, e=exe_name: self.remove_from_close_list(e))
            item_layout.addWidget(remove_btn)

            self.close_list_layout.addWidget(item_frame)

        self.close_list_layout.addStretch()

    def add_to_open_list(self, app_name, app_path, args=None):
        """Adds an app to the open list"""
        if args is None:
            args = []
        self.selected_open_apps[app_name] = {
            'path': app_path,
            'args': args
        }
        self.refresh_open_list()

    def remove_from_open_list(self, app_name):
        """Removes an app from the open list"""
        if app_name in self.selected_open_apps:
            del self.selected_open_apps[app_name]
        self.refresh_open_list()

    def refresh_open_list(self):
        """Refreshes visual list of apps to open"""
        # Limpiar
        while self.open_list_layout.count():
            child = self.open_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Agregar cada app seleccionada
        for app_name in sorted(self.selected_open_apps.keys()):
            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #1e1e1e; border: none; border-radius: 3px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)

            # Show name with complete validation
            display_text = str(app_name).strip() if app_name else '[Sin nombre]'
            if not display_text or display_text == '':
                display_text = f"App ({self.selected_open_apps[app_name].get('path', 'sin ruta')[:30]}...)"

            label = QLabel(display_text)
            label.setFont(QFont('Arial', 10))
            label.setMinimumWidth(100)
            label.setStyleSheet("color: white; background: transparent;")
            item_layout.addWidget(label)

            item_layout.addStretch()

            remove_btn = QPushButton("✕")
            remove_btn.setFont(QFont('Arial', 12, QFont.Bold))
            remove_btn.setStyleSheet("background-color: #1e1e1e; color: #3498db; border: none; min-width: 40px; min-height: 30px;")
            remove_btn.clicked.connect(lambda checked, n=app_name: self.remove_from_open_list(n))
            item_layout.addWidget(remove_btn)

            self.open_list_layout.addWidget(item_frame)

        self.open_list_layout.addStretch()

    def add_to_allowed_list(self, exe_name):
        """Adds an app to the allowed apps whitelist"""
        self.selected_allowed_apps.add(exe_name)
        self.refresh_allowed_list()

    def remove_from_allowed_list(self, exe_name):
        """Removes an app from the allowed apps whitelist"""
        if exe_name in self.selected_allowed_apps:
            self.selected_allowed_apps.remove(exe_name)
        self.refresh_allowed_list()

    def toggle_whitelist_widgets(self):
        """Show/hide whitelist widgets based on checkbox state"""
        is_enabled = self.whitelist_enabled_check.isChecked()

        # Show/hide only the button and list for allowed apps
        # Keep close/open columns visible but they won't be applied when whitelist is enabled
        self.add_allowed_btn.setVisible(is_enabled)
        self.allowed_scroll.setVisible(is_enabled)

    def refresh_allowed_list(self):
        """Refreshes visual list of allowed apps (whitelist)"""
        # Limpiar
        while self.allowed_list_layout.count():
            child = self.allowed_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Agregar cada app seleccionada
        for exe_name in sorted(self.selected_allowed_apps):
            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #1e1e1e; border: none; border-radius: 3px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)

            display_text = str(exe_name).strip() if exe_name else '[Sin nombre]'
            if not display_text:
                display_text = '[App sin nombre]'

            label = QLabel(display_text)
            label.setFont(QFont('Arial', 10))
            label.setMinimumWidth(100)
            label.setStyleSheet("color: white; background: transparent;")
            item_layout.addWidget(label)

            item_layout.addStretch()

            remove_btn = QPushButton("✕")
            remove_btn.setFont(QFont('Arial', 12, QFont.Bold))
            remove_btn.setStyleSheet("background-color: #1e1e1e; color: #3498db; border: none; min-width: 40px; min-height: 30px;")
            remove_btn.clicked.connect(lambda checked, e=exe_name: self.remove_from_allowed_list(e))
            item_layout.addWidget(remove_btn)

            self.allowed_list_layout.addWidget(item_frame)

        self.allowed_list_layout.addStretch()

    def refresh_browsers_list(self):
        """Refreshes visual list of configured browsers"""
        # Limpiar
        while self.browsers_list_layout.count():
            child = self.browsers_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Search for browsers in apps to open list
        browsers_added = []
        for app_name, app_data in self.selected_open_apps.items():
            # Check if it's a supported browser
            for browser_key in SUPPORTED_BROWSERS.keys():
                if browser_key in app_name.lower():
                    browsers_added.append((app_name, browser_key))
                    break

        if not browsers_added:
            # Show message if no browsers
            no_browser_label = QLabel(lang.get('no_browsers_configured'))
            no_browser_label.setFont(QFont('Arial', 10))
            no_browser_label.setStyleSheet("color: #95a5a6;")
            no_browser_label.setAlignment(Qt.AlignCenter)
            self.browsers_list_layout.addWidget(no_browser_label)
            return

        # Show each browser
        for app_name, browser_key in browsers_added:
            config = SUPPORTED_BROWSERS[browser_key]

            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #1e1e1e; border: none; border-radius: 3px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)

            # Name
            browser_name = str(config.get('name', browser_key)).strip()
            if not browser_name:
                browser_name = browser_key.upper()

            name_label = QLabel(browser_name)
            name_label.setFont(QFont('Arial', 11, QFont.Bold))
            name_label.setStyleSheet("color: white; background: transparent;")
            item_layout.addWidget(name_label)

            # Port
            port_label = QLabel(lang.get('port', port=config.get('port', '????')))
            port_label.setFont(QFont('Arial', 9))
            port_label.setStyleSheet("color: #95a5a6; background: transparent;")
            item_layout.addWidget(port_label)

            item_layout.addStretch()

            # Remove button - Same style as applications
            remove_btn = QPushButton("✕")
            remove_btn.setFont(QFont('Arial', 12, QFont.Bold))
            remove_btn.setStyleSheet("background-color: #1e1e1e; color: #3498db; border: none; min-width: 40px; min-height: 30px;")
            remove_btn.clicked.connect(lambda checked, n=app_name: self.remove_browser(n))
            item_layout.addWidget(remove_btn)

            self.browsers_list_layout.addWidget(item_frame)

    def remove_browser(self, app_name):
        """Removes a browser from the list"""
        self.remove_from_open_list(app_name)
        self.refresh_browsers_list()

    def add_browser_configured(self, browser_key):
        """Adds a browser with correct configuration automatically"""

        config = SUPPORTED_BROWSERS.get(browser_key)
        if not config:
            return

        # Check if this browser already exists
        if browser_key in self.selected_open_apps:
            QMessageBox.information(
                self,
                lang.get('browser_already_added', browser=config['name']),
                lang.get('browser_already_added_msg', browser=config['name'])
            )
            return

        try:
            # Auto-detect browser
            browser_path = BrowserDetector.find_browser(browser_key)

            if not browser_path:
                QMessageBox.critical(
                    self,
                    lang.get('browser_not_found', browser=config['name']),
                    lang.get('browser_not_found_msg', browser=config['name'])
                )
                return

            # Get recommended args
            args = BrowserDetector.get_recommended_args(browser_key)

            # Add to list
            self.add_to_open_list(browser_key, browser_path, args)

            QMessageBox.information(
                self,
                lang.get('browser_configured', browser=config['name']),
                lang.get('browser_configured_msg', browser=config['name'], path=browser_path, port=config['port'], profile=config['user_data_dir_name'])
            )

            # Refresh browser list
            self.refresh_browsers_list()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error al agregar navegador: {str(e)}"
            )

    def add_close_app_manual(self):
        """Search for an app to close using file explorer"""

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            lang.get('select_app_to_close'),
            "",
            lang.get('executables')
        )

        if filepath:
            exe_name = Path(filepath).name

            # Special warning if trying to close chrome.exe
            if exe_name.lower() == 'chrome.exe':
                chrome_in_open = any('chrome' in app.lower() for app in self.selected_open_apps.keys())

                if chrome_in_open:
                    reply = QMessageBox.question(
                        self,
                        lang.get('chrome_conflict_warning'),
                        lang.get('chrome_conflict_msg'),
                        QMessageBox.Yes | QMessageBox.No
                    )

                    if reply != QMessageBox.Yes:
                        return

            self.add_to_close_list(exe_name)

    def add_open_app_manual(self):
        """Search for an app to open using file explorer"""

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            lang.get('select_app_to_open'),
            "",
            lang.get('executables')
        )

        if filepath:
            app_name = Path(filepath).stem.lower()

            # BLOCK Chrome completely - must use special button
            if 'chrome' in app_name:
                QMessageBox.critical(
                    self,
                    lang.get('cannot_add_chrome_here'),
                    lang.get('cannot_add_chrome_msg')
                )
                return

            # Determine args
            args = []

            self.add_to_open_list(app_name, filepath, args)

    def add_allowed_app_manual(self):
        """Search for an app to add to whitelist using file explorer"""

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            lang.get('select_app_to_allow'),
            "",
            lang.get('executables')
        )

        if filepath:
            exe_name = Path(filepath).name
            self.add_to_allowed_list(exe_name)

    def on_ultra_domain_mode_changed(self, checked):
        """Callback when domain radio button changes"""
        # If "use current domain" is checked, disable field and button
        use_current = self.ultra_use_current.isChecked()
        self.ultra_domain_input.setEnabled(not use_current)
        self.ultra_capture_btn.setEnabled(not use_current)

    def capture_current_domain(self):
        """Captures domain from currently open browser"""
        from urllib.parse import urlparse

        # Try to get domain from any configured browser
        captured_domain = None

        for port in [9222, 9223, 9224]:  # Puertos de Chrome, Brave, Edge
            try:
                import requests
                response = requests.get(f'http://localhost:{port}/json', timeout=1)
                tabs = response.json()

                if tabs:
                    # Take first active tab
                    for tab in tabs:
                        if tab.get('type') == 'page':
                            url = tab.get('url', '')
                            if url and not url.startswith('chrome://') and not url.startswith('edge://'):
                                parsed = urlparse(url)
                                domain = parsed.netloc.lower()
                                if domain.startswith('www.'):
                                    domain = domain[4:]
                                captured_domain = domain
                                break

                if captured_domain:
                    break

            except Exception:
                continue

        if captured_domain:
            self.ultra_domain_input.setText(captured_domain)
            QMessageBox.information(
                self,
                lang.get('domain_captured'),
                f"{lang.get('domain_captured_msg')}\n\n{captured_domain}"
            )
        else:
            QMessageBox.warning(
                self,
                lang.get('no_browser_open'),
                lang.get('no_browser_open_msg')
            )

    def is_valid_domain(self, domain: str) -> bool:
        """Validates that domain has valid format"""
        import re

        # Basic pattern to validate domains
        # Allows: example.com, sub.example.com, sub.domain.example.com
        pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

        return bool(re.match(pattern, domain))

    def save_config(self):
        """Save configuration to JSON file"""

        # Final validation: Chrome in both lists
        chrome_in_close = any('chrome.exe' in app.lower() for app in self.selected_close_apps)
        chrome_in_open = any('chrome' in app.lower() for app in self.selected_open_apps.keys())

        if chrome_in_close and chrome_in_open:
            reply = QMessageBox.question(
                self,
                lang.get('conflicting_config'),
                lang.get('conflicting_config_msg'),
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        # Update mode data
        self.mode_data['name'] = self.name_entry.text()
        self.mode_data['strict_mode'] = self.strict_mode_check.isChecked()

        # Ultra Focus Mode checkbox (only if exists - doesn't exist in ultra_focus mode)
        if hasattr(self, 'ultra_focus_check') and self.ultra_focus_check is not None:
            try:
                self.mode_data['ultra_focus_mode'] = self.ultra_focus_check.isChecked()
            except RuntimeError:
                # Checkbox was deleted, skip
                pass

        # Ultra Focus Settings (if ultra focus configuration exists)
        if hasattr(self, 'ultra_domain_input') and hasattr(self, 'ultra_browser_combo'):
            if not 'ultra_focus_settings' in self.mode_data:
                self.mode_data['ultra_focus_settings'] = {}

            # Only save use_current_domain if radio button exists and is not deleted
            if hasattr(self, 'ultra_use_current') and self.ultra_use_current is not None:
                try:
                    self.mode_data['ultra_focus_settings']['use_current_domain'] = self.ultra_use_current.isChecked()
                except RuntimeError:
                    # Radio button was deleted, skip
                    pass

            # Safely get domain input
            try:
                self.mode_data['ultra_focus_settings']['locked_domain'] = self.ultra_domain_input.text().strip()
            except RuntimeError:
                pass

            # Safely get browser selection
            try:
                self.mode_data['ultra_focus_settings']['selected_browser'] = self.ultra_browser_combo.currentData()
            except RuntimeError:
                pass

            # Save close_all_non_browser_apps setting
            if hasattr(self, 'ultra_close_apps_check'):
                try:
                    self.mode_data['ultra_focus_settings']['close_all_non_browser_apps'] = self.ultra_close_apps_check.isChecked()
                except RuntimeError:
                    pass

            # Validate domain if one was specified
            use_current = self.mode_data['ultra_focus_settings'].get('use_current_domain', False)
            if not use_current:
                domain = self.mode_data['ultra_focus_settings'].get('locked_domain', '')
                if domain and not self.is_valid_domain(domain):
                    QMessageBox.warning(
                        self,
                        lang.get('invalid_domain'),
                        lang.get('invalid_domain_msg')
                    )
                    return

        # Apps to close
        self.mode_data['close'] = list(self.selected_close_apps)

        # Apps to open
        open_list = []
        for app_name, app_data in self.selected_open_apps.items():
            open_list.append({
                'name': app_name,
                'path': app_data['path'],
                'args': app_data.get('args', [])
            })
        self.mode_data['open'] = open_list

        # Allowed apps (whitelist) and whitelist enabled flag
        if self.whitelist_enabled_check is not None:
            self.mode_data['whitelist_enabled'] = self.whitelist_enabled_check.isChecked()
        self.mode_data['allowed_apps'] = list(self.selected_allowed_apps)

        # Guardar en archivo JSON (AppData persistent location)
        import os
        app_data = Path(os.getenv('LOCALAPPDATA')) / 'FocusManager' / 'modes'
        app_data.mkdir(parents=True, exist_ok=True)
        mode_file = app_data / f'{self.mode_id}.json'

        try:
            with open(mode_file, 'w', encoding='utf-8') as f:
                json.dump(self.mode_data, f, indent=2, ensure_ascii=False)

            # Llamar callback
            if self.on_save:
                self.on_save()

            # Show success message without closing
            success_msg = "Cambios guardados exitosamente" if lang.get_current_language() == 'es' else "Changes saved successfully"
            QMessageBox.information(self, lang.get('success'), success_msg)

            # Don't close the window - user can continue editing or close manually
            # self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", lang.get('config_save_error', error=str(e)))

    def open_browser_whitelist(self):
        """Abre la ventana para configurar sitios web permitidos"""
        try:
            from browser_whitelist_window import BrowserWhitelistWindow
            whitelist_window = BrowserWhitelistWindow(self, self.mode_data.get('name', self.mode_id))
            whitelist_window.exec()
        except ImportError as e:
            QMessageBox.critical(
                self,
                lang.get('module_not_available'),
                lang.get('whitelist_module_error', error=str(e))
            )
