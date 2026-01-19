"""
About Dialog - Developer information
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtSvgWidgets import QSvgWidget
from pathlib import Path
from translations import lang


class AboutDialog(QDialog):
    """About window with tabs (About, Thanks To, License)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.get('about_title'))
        self.setFixedSize(500, 400)
        self.setModal(True)

        # Set window icon
        icon_path = Path(__file__).parent / 'icons' / 'logo.svg'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.create_widgets()

    def create_widgets(self):
        """Creates the dialog interface"""

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Simple header with logo and version
        header_layout = QHBoxLayout()

        # Logo SVG
        logo_path = Path(__file__).parent / 'icons' / 'logo.svg'
        if logo_path.exists():
            logo_svg = QSvgWidget(str(logo_path))
            logo_svg.setFixedSize(64, 64)
            header_layout.addWidget(logo_svg)
        else:
            # Fallback to emoji if SVG not found
            logo_label = QLabel("⚡")
            logo_label.setFont(QFont('Arial', 48))
            header_layout.addWidget(logo_label)

        # Version info
        info_layout = QVBoxLayout()

        title_label = QLabel("System Focus Manager")
        title_label.setFont(QFont('Arial', 12, QFont.Bold))
        info_layout.addWidget(title_label)

        version_label = QLabel("Version 2.0 (2025-12-29)")
        version_label.setFont(QFont('Arial', 9))
        info_layout.addWidget(version_label)

        info_layout.addStretch()
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Tabs
        tabs = QTabWidget()

        # Tab 1: About
        about_widget = self.create_about_tab()
        tabs.addTab(about_widget, lang.get('about_tab'))

        # Tab 2: License
        license_widget = self.create_license_tab()
        tabs.addTab(license_widget, lang.get('license_tab'))

        layout.addWidget(tabs)

        # Centered OK button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.setMinimumHeight(30)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_about_tab(self):
        """Creates the About tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        # Program description
        desc = QLabel(
            f"System Focus Manager\n\n"
            f"{lang.get('about_description')}\n\n"
            f"{lang.get('about_programmed')}\n"
            f"Manuela Riascos Hurtado\n\n"
            f"{lang.get('about_contact')} manhurta54@gmail.com\n\n"
            f"{lang.get('about_based')}\n\n"
            f"{lang.get('about_project_home')} https://github.com/Elah2022\n\n"
            f"{lang.get('about_copyright')}"
        )
        desc.setFont(QFont('Arial', 9))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignLeft)
        layout.addWidget(desc)

        layout.addStretch()

        return widget

    def create_license_tab(self):
        """Creates the License tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setPlainText(
            f"{lang.get('license_description')}\n\n"

            "MIT LICENSE\n\n"
            "Copyright (c) 2025 Manuela Riascos Hurtado\n\n"

            "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
            "of this software and associated documentation files (the \"Software\"), to deal\n"
            "in the Software without restriction, including without limitation the rights\n"
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
            "copies of the Software, and to permit persons to whom the Software is\n"
            "furnished to do so, subject to the following conditions:\n\n"

            "The above copyright notice and this permission notice shall be included in all\n"
            "copies or substantial portions of the Software.\n\n"

            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
            "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
            "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
            "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
            "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
            "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
            "SOFTWARE."
        )
        license_text.setFont(QFont('Courier New', 8))
        layout.addWidget(license_text)

        return widget


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    dialog = AboutDialog()
    dialog.show()
    sys.exit(app.exec())
