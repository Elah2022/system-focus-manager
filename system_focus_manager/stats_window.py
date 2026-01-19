"""
Usage statistics display with Audit Log.
Shows time spent in each mode, closed apps, and audit trail.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QScrollArea, QWidget, QFileDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QComboBox
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
        # Set dark background for entire dialog
        self.setStyleSheet("")

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
        tabs.setStyleSheet("")

        # Tab 1: Statistics (existing content)
        stats_tab = self.create_stats_tab()
        tabs.addTab(stats_tab, "Statistics")

        # Tab 2: Audit Log (new)
        audit_tab = self.create_audit_tab()
        tabs.addTab(audit_tab, "Audit Log")

        layout.addWidget(tabs)

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
        summary_group.setStyleSheet("")
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
        modes_group.setStyleSheet("")
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
        apps_group.setStyleSheet("")
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
        scroll_layout.addWidget(apps_group)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return widget

    def create_audit_tab(self):
        """Create audit log tab showing suspicious activities"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Filter controls
        filter_frame = QFrame()
        filter_frame.setStyleSheet("padding: 10px;")
        filter_layout = QHBoxLayout(filter_frame)

        # Event type filter
        event_label = QLabel("Filter by Event:")
        event_label.setFont(QFont('Arial', 10))
        event_label.setStyleSheet("")
        filter_layout.addWidget(event_label)

        from PySide6.QtWidgets import QComboBox
        self.event_filter = QComboBox()
        self.event_filter.addItems(["All Events", "Abrupt Closures Only", "Activations Only", "Deactivations Only"])
        self.event_filter.setFont(QFont('Arial', 10))
        self.event_filter.setStyleSheet("")
        self.event_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.event_filter)

        filter_layout.addSpacing(20)

        # Sort label
        sort_label = QLabel("Sort:")
        sort_label.setFont(QFont('Arial', 10))
        sort_label.setStyleSheet("")
        filter_layout.addWidget(sort_label)

        # Sort dropdown
        self.sort_filter = QComboBox()
        self.sort_filter.addItems(["Descending", "Ascending"])
        self.sort_filter.setFont(QFont('Arial', 10))
        self.sort_filter.setStyleSheet("")
        self.sort_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.sort_filter)

        filter_layout.addStretch()

        layout.addWidget(filter_frame)

        # Create table
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(4)
        self.audit_table.setHorizontalHeaderLabels(["Time", "Event", "Mode", "Details"])
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.audit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.audit_table.setAlternatingRowColors(False)
        self.audit_table.setFont(QFont('Arial', 9))
        self.audit_table.setShowGrid(False)
        self.audit_table.setStyleSheet("QTableWidget::item:selected { background-color: #3498db; color: white; }")

        # Store all audit log entries for filtering
        self.all_audit_entries = self.audit_log.copy()

        # Populate table
        self.populate_audit_table(self.audit_log)

        # Resize columns
        self.audit_table.setColumnWidth(0, 130)
        self.audit_table.setColumnWidth(1, 150)
        self.audit_table.setColumnWidth(2, 120)

        layout.addWidget(self.audit_table)

        # Summary of suspicious events
        self.summary_label = QLabel()
        self.summary_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.update_summary_label(self.audit_log)
        layout.addWidget(self.summary_label)

        # Action buttons
        button_layout = QHBoxLayout()

        delete_selected_btn = QPushButton("Delete Selected")
        delete_selected_btn.setFont(QFont('Arial', 10))
        delete_selected_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 35px;")
        delete_selected_btn.clicked.connect(self.delete_selected_audit_event)
        button_layout.addWidget(delete_selected_btn)

        clear_all_btn = QPushButton("Clear All (Requires PIN)")
        clear_all_btn.setFont(QFont('Arial', 10))
        clear_all_btn.setStyleSheet("background-color: #3498db; color: white; min-height: 35px;")
        clear_all_btn.clicked.connect(self.clear_all_audit_log)
        button_layout.addWidget(clear_all_btn)

        layout.addLayout(button_layout)

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

    def delete_selected_audit_event(self):
        """Delete the selected audit log event (requires PIN)"""
        # Check if a row is selected
        selected_rows = self.audit_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select an event to delete."
            )
            return

        # Get the row number
        row = selected_rows[0].row()

        # Get the timestamp from the first column
        timestamp_item = self.audit_table.item(row, 0)
        timestamp = timestamp_item.data(Qt.UserRole)

        # Verify PIN
        from pin_manager import PINManager
        pin_mgr = PINManager()

        if pin_mgr.is_pin_enabled():
            from PySide6.QtWidgets import QInputDialog, QLineEdit

            pin, ok = QInputDialog.getText(
                self,
                "PIN Required",
                "Enter PIN to delete this event:",
                QLineEdit.Password
            )

            if not ok:
                return

            if not pin_mgr.verify_pin(pin):
                QMessageBox.critical(
                    self,
                    "Access Denied",
                    "Incorrect PIN!"
                )
                return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            lang.get("are_you_sure_delete_event"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete from database
                self.stats_manager.delete_audit_event(timestamp)

                # Remove from table
                self.audit_table.removeRow(row)

                # Reload audit log data
                self.audit_log = self.stats_manager.get_audit_log(days=7)

                QMessageBox.information(
                    self,
                    "Success",
                    "Event deleted successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete event: {str(e)}"
                )

    def clear_all_audit_log(self):
        """Clear all audit log entries (requires PIN)"""
        # Verify PIN
        from pin_manager import PINManager
        pin_mgr = PINManager()

        if not pin_mgr.is_pin_enabled():
            QMessageBox.warning(
                self,
                "PIN Required",
                "You must set a PIN before clearing the audit log.\nGo to Settings to set a PIN."
            )
            return

        from PySide6.QtWidgets import QInputDialog, QLineEdit

        pin, ok = QInputDialog.getText(
            self,
            "PIN Required",
            "Enter PIN to clear all audit log entries:",
            QLineEdit.Password
        )

        if not ok:
            return

        if not pin_mgr.verify_pin(pin):
            QMessageBox.critical(
                self,
                "Access Denied",
                "Incorrect PIN!"
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Clear All",
            "Are you sure you want to DELETE ALL audit log entries?\n\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Clear all from database
                self.stats_manager.clear_all_audit_log()

                # Clear table
                self.audit_table.setRowCount(0)

                # Reload audit log data
                self.audit_log = []

                QMessageBox.information(
                    self,
                    "Success",
                    "All audit log entries have been cleared."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear audit log: {str(e)}"
                )

    def populate_audit_table(self, entries):
        """Populate the audit table with the given entries"""
        self.audit_table.setRowCount(len(entries))

        for row, entry in enumerate(entries):
            # Time
            timestamp = entry.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                time_str = str(timestamp)[:16]

            time_item = QTableWidgetItem(time_str)
            time_item.setFont(QFont('Courier New', 9))
            # Store timestamp as user data for deletion
            time_item.setData(Qt.UserRole, timestamp)

            # Event type
            event_type = entry.get('event_type', '')
            severity = entry.get('severity', 'normal')
            description = entry.get('description', '')

            # Remove triangle emojis from description
            description = description.replace('⚠️', '').strip()

            if event_type == 'ABRUPT_CLOSURE':
                if 'shut down' in description.lower() or 'restart' in description.lower():
                    event_text = "SHUTDOWN/RESTART"
                else:
                    event_text = "CLOSED UNEXPECTEDLY"
            elif event_type == 'MODE_ACTIVATED':
                event_text = "Activated"
            elif event_type == 'MODE_DEACTIVATED':
                event_text = "Deactivated"
            elif event_type == 'APP_CLOSED':
                event_text = "App Closed"
            else:
                event_text = event_type

            # Time item - normal
            # (no special styling needed, will use default)

            # Event item - RED BACKGROUND ONLY for abrupt closures
            event_item = QTableWidgetItem(event_text)
            event_item.setFont(QFont('Arial', 9, QFont.Bold))
            if event_type == 'ABRUPT_CLOSURE':
                event_item.setBackground(QColor(220, 53, 69))  # Bright red background
                event_item.setForeground(QColor('white'))  # White text on red background
            # Other event types use default styling

            # Mode name - normal
            mode_name = entry.get('mode_name', '-')
            mode_item = QTableWidgetItem(mode_name)

            # Description - RED BACKGROUND for abrupt closures
            desc_item = QTableWidgetItem(description)
            if event_type == 'ABRUPT_CLOSURE':
                desc_item.setBackground(QColor(220, 53, 69))  # Bright red background
                desc_item.setForeground(QColor('white'))  # White text on red background

            self.audit_table.setItem(row, 0, time_item)
            self.audit_table.setItem(row, 1, event_item)
            self.audit_table.setItem(row, 2, mode_item)
            self.audit_table.setItem(row, 3, desc_item)

    def update_summary_label(self, entries):
        """Update the summary label based on filtered entries"""
        suspicious_count = sum(1 for e in entries if e.get('severity') == 'suspicious')
        if suspicious_count > 0:
            self.summary_label.setText(f"{suspicious_count} suspicious event(s) detected (possible cheating attempts)")
            self.summary_label.setStyleSheet("padding: 10px; background-color: #ffcccc; color: #c0392b;")
        else:
            self.summary_label.setText("No suspicious activity detected")
            self.summary_label.setStyleSheet("padding: 10px; background-color: #d5f4e6; color: #27ae60;")

    def apply_filters(self):
        """Apply selected filters to the audit log"""
        filtered_entries = self.all_audit_entries.copy()

        # Filter by event type
        event_filter = self.event_filter.currentText()
        if event_filter == "Abrupt Closures Only":
            filtered_entries = [e for e in filtered_entries if e.get('event_type') == 'ABRUPT_CLOSURE']
        elif event_filter == "Activations Only":
            filtered_entries = [e for e in filtered_entries if e.get('event_type') == 'MODE_ACTIVATED']
        elif event_filter == "Deactivations Only":
            filtered_entries = [e for e in filtered_entries if e.get('event_type') == 'MODE_DEACTIVATED']
        # "All Events" shows everything, no filtering needed

        # Sort by date
        sort_order = self.sort_filter.currentText()
        if sort_order == "Ascending":
            # Sort ascending (oldest first)
            filtered_entries = sorted(filtered_entries, key=lambda x: x.get('timestamp', ''))
        else:
            # Sort descending (newest first) - default
            filtered_entries = sorted(filtered_entries, key=lambda x: x.get('timestamp', ''), reverse=True)

        # Update table and summary
        self.populate_audit_table(filtered_entries)
        self.update_summary_label(filtered_entries)
