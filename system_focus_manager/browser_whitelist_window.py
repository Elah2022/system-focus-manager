"""
Window to configure website whitelist per mode.
Allows users to add/remove permitted sites.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QWidget, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtSvgWidgets import QSvgWidget
import json
from pathlib import Path
from translations import lang


class BrowserWhitelistWindow(QDialog):
    """Window to configure which websites to allow in each mode"""

    def __init__(self, parent, mode_name):
        super().__init__(parent)
        self.mode_name = mode_name

        # Load current rules from AppData (persistent location)
        import os
        app_data = Path(os.getenv('LOCALAPPDATA')) / 'FocusManager'
        app_data.mkdir(parents=True, exist_ok=True)
        self.rules_file = app_data / 'rules.json'
        self.load_rules()

        # Create window
        self.setWindowTitle(lang.get('browser_whitelist_title', mode=mode_name))
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        self.setModal(True)

        # Set window icon
        icon_path = Path(__file__).parent / 'icons' / 'logo.svg'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.create_widgets()

    def load_rules(self):
        """Loads rules from JSON file"""
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.all_rules = data
                mode_key = self.mode_name.lower()
                self.allowed_sites = data.get('mode_whitelists', {}).get(mode_key, [])
        except FileNotFoundError:
            # Create default file
            self.all_rules = {
                'mode_whitelists': {},
                'global_exceptions': ['localhost', '127.0.0.1'],
                'config': {
                    'debugging_port': 9222,
                    'monitoring_interval_seconds': 10,
                    'show_notifications': True
                }
            }
            self.allowed_sites = []

    def create_widgets(self):
        """Creates the interface"""

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2c3e50; min-height: 40px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)

        # Title (no logo - just text)
        header_text = f"SITIOS WEB PERMITIDOS - {self.mode_name.upper()}" if lang.get_current_language() == 'es' else f"ALLOWED WEBSITES - {self.mode_name.upper()}"
        header_label = QLabel(header_text)
        header_label.setFont(QFont('Arial', 12, QFont.Bold))
        header_label.setStyleSheet("color: white;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Instructions
        info_group = QGroupBox()
        info_group.setStyleSheet("QGroupBox { border: none; }")
        info_layout = QVBoxLayout()

        info1 = QLabel(lang.get('whitelist_info1'))
        info1.setFont(QFont('Arial', 10))
        info1.setStyleSheet("color: white;")
        info_layout.addWidget(info1)

        info2 = QLabel(lang.get('whitelist_info2'))
        info2.setFont(QFont('Arial', 10))
        info2.setStyleSheet("color: white;")
        info_layout.addWidget(info2)

        info3 = QLabel(lang.get('whitelist_info3'))
        info3.setFont(QFont('Arial', 9))
        info3.setStyleSheet("color: white; font-style: italic;")
        info_layout.addWidget(info3)

        info_group.setLayout(info_layout)
        scroll_layout.addWidget(info_group)

        # Frame to add new site
        add_group = QGroupBox(lang.get('add_new_site'))
        add_group.setFont(QFont('Arial', 10, QFont.Bold))
        add_group.setStyleSheet("QGroupBox { border: none; padding-top: 5px; }")
        add_layout = QVBoxLayout()

        input_layout = QHBoxLayout()

        label = QLabel(lang.get('domain_label'))
        label.setFont(QFont('Arial', 10))
        input_layout.addWidget(label)

        self.domain_entry = QLineEdit()
        self.domain_entry.setFont(QFont('Arial', 11))
        self.domain_entry.setPlaceholderText(lang.get('domain_placeholder'))
        self.domain_entry.returnPressed.connect(self.add_site)
        input_layout.addWidget(self.domain_entry)

        # Remove emoji and change to blue
        add_text = "Agregar" if lang.get_current_language() == 'es' else "Add"
        add_btn = QPushButton(add_text)
        add_btn.setFont(QFont('Arial', 10, QFont.Bold))
        add_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 30px;")
        add_btn.clicked.connect(self.add_site)
        input_layout.addWidget(add_btn)

        add_layout.addLayout(input_layout)

        # Examples
        examples_layout = QHBoxLayout()

        examples_label = QLabel(lang.get('examples_label'))
        examples_label.setFont(QFont('Arial', 9))
        examples_label.setStyleSheet("color: #7f8c8d;")
        examples_layout.addWidget(examples_label)

        for example in ["github.com", "stackoverflow.com", "google.com"]:
            example_btn = QPushButton(example)
            example_btn.setFont(QFont('Arial', 8))
            example_btn.setStyleSheet("border: none; color: #3498db; text-decoration: underline;")
            example_btn.clicked.connect(lambda checked, e=example: self.domain_entry.setText(e))
            example_btn.setCursor(Qt.PointingHandCursor)
            examples_layout.addWidget(example_btn)

        examples_layout.addStretch()
        add_layout.addLayout(examples_layout)

        add_group.setLayout(add_layout)
        scroll_layout.addWidget(add_group)

        # List of allowed sites
        self.list_group = QGroupBox(lang.get('allowed_sites_count', count=len(self.allowed_sites)))
        self.list_group.setFont(QFont('Arial', 10, QFont.Bold))
        self.list_group.setStyleSheet("QGroupBox { border: none; padding-top: 5px; }")
        list_main_layout = QVBoxLayout()

        # Internal scrollbar
        self.sites_scroll = QScrollArea()
        self.sites_scroll.setWidgetResizable(True)
        self.sites_list_widget = QWidget()
        self.sites_list_layout = QVBoxLayout(self.sites_list_widget)
        self.sites_scroll.setWidget(self.sites_list_widget)

        list_main_layout.addWidget(self.sites_scroll)
        self.list_group.setLayout(list_main_layout)
        scroll_layout.addWidget(self.list_group)

        self.refresh_sites_list()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Action buttons
        action_layout = QHBoxLayout()

        save_text = "GUARDAR CAMBIOS" if lang.get_current_language() == 'es' else "SAVE CHANGES"
        save_btn = QPushButton(save_text)
        save_btn.setFont(QFont('Arial', 11, QFont.Bold))
        save_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        save_btn.clicked.connect(self.save_changes)
        action_layout.addWidget(save_btn)

        cancel_btn = QPushButton(lang.get('cancel'))
        cancel_btn.setFont(QFont('Arial', 11))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)

        layout.addLayout(action_layout)

        self.setLayout(layout)

    def add_site(self):
        """Adds a site to the list"""
        domain = self.domain_entry.text().strip().lower()

        if not domain:
            QMessageBox.warning(
                self,
                lang.get('field_empty'),
                lang.get('field_empty_message')
            )
            return

        # Clean domain (remove https://, www., etc)
        domain = domain.replace('https://', '').replace('http://', '')
        domain = domain.replace('www.', '')
        domain = domain.split('/')[0]  # Only domain, no paths

        # Validate basic format
        if '.' not in domain:
            QMessageBox.critical(
                self,
                lang.get('domain_invalid'),
                lang.get('domain_invalid_message', domain=domain)
            )
            return

        # Check if already exists
        if domain in self.allowed_sites:
            QMessageBox.information(
                self,
                lang.get('domain_exists'),
                lang.get('domain_exists_message', domain=domain)
            )
            return

        # Agregar
        self.allowed_sites.append(domain)
        self.domain_entry.clear()
        self.refresh_sites_list()

    def remove_site(self, domain):
        """Removes a site from the list"""
        if domain in self.allowed_sites:
            self.allowed_sites.remove(domain)
            self.refresh_sites_list()

    def refresh_sites_list(self):
        """Refreshes the visual list"""
        # Clear
        while self.sites_list_layout.count():
            child = self.sites_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Update title
        self.list_group.setTitle(lang.get('allowed_sites_count', count=len(self.allowed_sites)))

        # If empty
        if not self.allowed_sites:
            empty_label = QLabel(lang.get('no_sites_warning'))
            empty_label.setFont(QFont('Arial', 10))
            empty_label.setStyleSheet("color: #e74c3c; font-style: italic;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.sites_list_layout.addWidget(empty_label)
            return

        # Add each site
        for domain in sorted(self.allowed_sites):
            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #000000; border: none; border-radius: 3px;")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)

            domain_text = str(domain).strip() if domain else '[Sitio sin nombre]'
            if not domain_text:
                domain_text = '[Vacío]'

            domain_label = QLabel(f"{domain_text}")
            domain_label.setFont(QFont('Arial', 10))
            domain_label.setMinimumWidth(150)
            domain_label.setStyleSheet("color: white; background: transparent;")
            item_layout.addWidget(domain_label)

            item_layout.addStretch()

            remove_btn = QPushButton("✕")
            remove_btn.setFont(QFont('Arial', 12, QFont.Bold))
            remove_btn.setStyleSheet("background-color: #000000; color: #3498db; border: none; min-width: 40px; min-height: 30px;")
            remove_btn.clicked.connect(lambda checked, d=domain: self.remove_site(d))
            item_layout.addWidget(remove_btn)

            self.sites_list_layout.addWidget(item_frame)

    def save_changes(self):
        """Saves changes to JSON file"""
        try:
            mode_key = self.mode_name.lower()

            # Update rules
            if 'mode_whitelists' not in self.all_rules:
                self.all_rules['mode_whitelists'] = {}

            self.all_rules['mode_whitelists'][mode_key] = self.allowed_sites

            # Save file
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_rules, f, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self,
                lang.get('saved_title'),
                lang.get('saved_message', mode=self.mode_name, count=len(self.allowed_sites))
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                lang.get('error_title'),
                lang.get('save_error', error=str(e))
            )


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = BrowserWhitelistWindow(None, "Focus")
    window.show()
    sys.exit(app.exec())
