"""
Usage statistics display with Audit Log.
Shows time spent in each mode, closed apps, and audit trail.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QScrollArea, QWidget, QFileDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QColor
from datetime import datetime
from pathlib import Path
from translations import lang


class StatsWindow(QDialog):
    """Window to display statistics and audit log"""

    def __init__(self, parent, stats_manager):
        super().__init__(parent)
        self.stats_manager = stats_manager

        # Create the window
        self.setWindowTitle(lang.get('stats_title'))
        self.setFixedSize(700, 650)

        # Set window icon
        try:
            from gui import get_resource_path
            stats_icon_path = get_resource_path('icons') / 'stadistics.svg'
        except:
            stats_icon_path = Path(__file__).parent / 'icons' / 'stadistics.svg'

        if stats_icon_path.exists():
            self.setWindowIcon(QIcon(str(stats_icon_path)))

        # Load data
        self.stats = self.stats_manager.get_stats_this_week()
        self.audit_log = self.stats_manager.get_audit_log(days=7)

        # Create interface
        self.create_widgets()

    def create_widgets(self):
        """Creates all visual elements with tabs"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #3498db; min-height: 50px;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 5, 10, 5)

        title_label = QLabel("Statistics & Audit Log")
        title_label.setFont(QFont('Arial', 18, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)

        layout.addWidget(title_frame)

        # Create tabs
        tabs = QTabWidget()
        tabs.setFont(QFont('Arial', 10))

        # Tab 1: Statistics (existing content)
        stats_tab = self.create_stats_tab()
        tabs.addTab(stats_tab, "📊 Statistics")

        # Tab 2: Audit Log (new)
        audit_tab = self.create_audit_tab()
        tabs.addTab(audit_tab, "🔍 Audit Log")

        layout.addWidget(tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont('Arial', 11))
        close_btn.setMinimumHeight(40)
        close_btn.setStyleSheet("background-color: #95a5a6; color: white;")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

    def create_stats_tab(self):
        """Create statistics tab (original content)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # General summary
        summary_group = QGroupBox("General Summary")
        summary_group.setFont(QFont('Arial', 11, QFont.Bold))
        summary_layout = QVBoxLayout()

        total_sessions = self.stats.get('total_sessions', 0)
        total_hours = self.stats.get('total_hours', 0)

        summary_text = f"""Total Sessions: {total_sessions}
Total Focus Time: {total_hours} hours
Average per Session: {round(total_hours / max(total_sessions, 1), 1)} hours"""

        summary_label = QLabel(summary_text.strip())
        summary_label.setFont(QFont('Arial', 13))
        summary_layout.addWidget(summary_label)

        summary_group.setLayout(summary_layout)
        scroll_layout.addWidget(summary_group)

        # Time per mode
        modes_group = QGroupBox("Time per Mode")
        modes_group.setFont(QFont('Arial', 11, QFont.Bold))
        modes_layout = QVBoxLayout()

        modes_data = self.stats.get('modes', {})

        if modes_data:
            for mode_name, data in modes_data.items():
                sessions = data.get('sessions', 0)
                hours = data.get('hours', 0)

                bar_length = int((hours / max(self.stats.get('total_hours', 1), 1)) * 30)
                bar = '█' * bar_length + '░' * (30 - bar_length)

                mode_text = f"{mode_name.upper():<12} {bar}  {hours}h ({sessions} sessions)"

                mode_label = QLabel(mode_text)
                mode_label.setFont(QFont('Courier New', 11))
                modes_layout.addWidget(mode_label)
        else:
            no_data_label = QLabel("No data yet")
            no_data_label.setFont(QFont('Arial', 10))
            no_data_label.setStyleSheet("color: #95a5a6;")
            modes_layout.addWidget(no_data_label)

        modes_group.setLayout(modes_layout)
        scroll_layout.addWidget(modes_group)

        # Most closed apps
        apps_group = QGroupBox("Most Closed Apps")
        apps_group.setFont(QFont('Arial', 11, QFont.Bold))
        apps_layout = QVBoxLayout()

        most_closed = self.stats.get('most_closed_apps', [])

        if most_closed:
            for i, app_data in enumerate(most_closed, 1):
                app_name = app_data.get('app', 'Unknown')
                count = app_data.get('count', 0)

                app_label = QLabel(f"{i}. {app_name} - {count} times")
                app_label.setFont(QFont('Arial', 12))
                apps_layout.addWidget(app_label)
        else:
            no_apps_label = QLabel("No data yet")
            no_apps_label.setFont(QFont('Arial', 10))
            no_apps_label.setStyleSheet("color: #95a5a6;")
            apps_layout.addWidget(no_apps_label)

        apps_group.setLayout(apps_layout)
        scroll_layout.addWidget(apps_layout)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Export button
        export_btn = QPushButton("Export Statistics")
        export_btn.setFont(QFont('Arial', 11, QFont.Bold))
        export_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 40px;")
        export_btn.clicked.connect(self.export_stats)
        layout.addWidget(export_btn)

        return widget

    def create_audit_tab(self):
        """Create audit log tab showing suspicious activities"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Info label
        info_label = QLabel("🔍 Activity Log - Detects abrupt closures (End Task, crashes, restarts)")
        info_label.setFont(QFont('Arial', 10))
        info_label.setStyleSheet("padding: 10px; background-color: #ecf0f1;")
        layout.addWidget(info_label)

        # Create table
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Time", "Event", "Mode", "Details"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setFont(QFont('Arial', 9))

        # Populate table
        table.setRowCount(len(self.audit_log))

        for row, entry in enumerate(self.audit_log):
            # Time
            timestamp = entry.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                time_str = str(timestamp)[:16]

            time_item = QTableWidgetItem(time_str)
            time_item.setFont(QFont('Courier New', 9))

            # Event type with icon
            event_type = entry.get('event_type', '')
            severity = entry.get('severity', 'normal')

            if event_type == 'ABRUPT_CLOSURE':
                event_text = "🚨 ABRUPT CLOSURE"
                bg_color = QColor(255, 200, 200)  # Light red
            elif event_type == 'MODE_ACTIVATED':
                event_text = "✅ Activated"
                bg_color = QColor(200, 255, 200)  # Light green
            elif event_type == 'MODE_DEACTIVATED':
                event_text = "⏹️ Deactivated"
                bg_color = QColor(200, 220, 255)  # Light blue
            else:
                event_text = event_type
                bg_color = QColor(255, 255, 255)  # White

            event_item = QTableWidgetItem(event_text)
            event_item.setBackground(bg_color)
            event_item.setFont(QFont('Arial', 9, QFont.Bold))

            # Mode name
            mode_name = entry.get('mode_name', '-')
            mode_item = QTableWidgetItem(mode_name)

            # Description
            description = entry.get('description', '')
            desc_item = QTableWidgetItem(description)

            table.setItem(row, 0, time_item)
            table.setItem(row, 1, event_item)
            table.setItem(row, 2, mode_item)
            table.setItem(row, 3, desc_item)

        # Resize columns
        table.setColumnWidth(0, 130)
        table.setColumnWidth(1, 150)
        table.setColumnWidth(2, 120)

        layout.addWidget(table)

        # Summary of suspicious events
        suspicious_count = sum(1 for e in self.audit_log if e.get('severity') == 'suspicious')
        if suspicious_count > 0:
            warning_label = QLabel(f"⚠️ {suspicious_count} suspicious event(s) detected (possible cheating attempts)")
            warning_label.setFont(QFont('Arial', 10, QFont.Bold))
            warning_label.setStyleSheet("padding: 10px; background-color: #ffcccc; color: #c0392b;")
            layout.addWidget(warning_label)
        else:
            ok_label = QLabel("✅ No suspicious activity detected")
            ok_label.setFont(QFont('Arial', 10))
            ok_label.setStyleSheet("padding: 10px; background-color: #d5f4e6; color: #27ae60;")
            layout.addWidget(ok_label)

        return widget

    def export_stats(self):
        """Exports statistics to a JSON file"""
        filename = f"focus_stats_{datetime.now().strftime('%Y-%m-%d')}.json"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            filename,
            "JSON files (*.json);;All files (*.*)"
        )

        if filepath:
            try:
                self.stats_manager.export_to_json(filepath)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Statistics exported to:\n{filepath}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Export error: {str(e)}"
                )
