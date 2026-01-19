"""
Here I handle the icon in the system tray (System Tray).
Allows minimizing to the tray and controlling the app from there.
"""

import pystray
from PIL import Image, ImageDraw
from threading import Thread
from pathlib import Path


class SystemTrayIcon:
    """My icon in the system tray"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.icon = None
        self.running = False

    def create_icon_image(self):
        """Create the icon for the tray"""
        # Create a simple lightning bolt icon similar to the logo
        width = 64
        height = 64

        # Create image with transparent background
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        dc = ImageDraw.Draw(image)

        # Draw a lightning bolt shape in yellow (like the logo)
        bolt_points = [
            (40, 10),   # top
            (28, 32),   # upper left
            (36, 32),   # upper right point
            (20, 54),   # bottom left
            (32, 36),   # middle left
            (40, 36),   # middle right
        ]
        dc.polygon(bolt_points, fill='#FFDD09', outline='#000000', width=2)

        return image

    def on_quit_clicked(self, icon, item):
        """When Exit is clicked from the tray"""
        from PySide6.QtCore import QMetaObject, Qt
        from PySide6.QtWidgets import QMessageBox

        # DON'T stop the tray icon - only stop if user successfully quits
        # Check if there's an active mode
        if hasattr(self.app, 'current_mode') and self.app.current_mode:
            # If PIN is enabled, verify it
            if self.app.pin_manager.is_pin_enabled():
                # Use QMetaObject.invokeMethod to run in main thread
                QMetaObject.invokeMethod(
                    self.app,
                    "_quit_with_pin_check",
                    Qt.QueuedConnection
                )
            else:
                # There's an active mode but no PIN - warn the user
                QMetaObject.invokeMethod(
                    self.app,
                    "_warn_active_mode_quit",
                    Qt.QueuedConnection
                )
        else:
            # No active mode, just quit
            QMetaObject.invokeMethod(
                self.app,
                "_safe_quit",
                Qt.QueuedConnection
            )

    def on_show_clicked(self, icon, item):
        """When Show is clicked"""
        from PySide6.QtCore import QMetaObject, Qt

        # Show window in main thread
        QMetaObject.invokeMethod(
            self.app,
            "_show_from_tray",
            Qt.QueuedConnection
        )

    def create_menu(self):
        """Create the icon menu"""
        from translations import lang

        menu_items = [
            pystray.MenuItem(lang.get('show') if hasattr(lang, 'get') else "Show", self.on_show_clicked)
        ]

        # Only show Exit option if there's NO active mode or PIN is not enabled
        if not (hasattr(self.app, 'current_mode') and self.app.current_mode and self.app.pin_manager.is_pin_enabled()):
            menu_items.append(
                pystray.MenuItem(lang.get('exit') if hasattr(lang, 'get') else "Exit", self.on_quit_clicked)
            )
        else:
            # Show a disabled "Exit (Protected)" option to indicate it's blocked
            menu_items.append(
                pystray.MenuItem("Exit (Protected by PIN)", None, enabled=False)
            )

        return pystray.Menu(*menu_items)

    def update_menu(self):
        """Update the menu when mode state changes"""
        if self.icon and self.running:
            self.icon.menu = self.create_menu()
            self.icon.update_menu()

    def start(self):
        """Start the icon in the tray"""
        if self.running:
            return

        self.running = True
        image = self.create_icon_image()
        menu = self.create_menu()

        self.icon = pystray.Icon(
            "FocusManager",
            image,
            "System Focus Manager",
            menu
        )

        # Run in separate thread
        thread = Thread(target=self.icon.run, daemon=True)
        thread.start()

    def stop(self):
        """Stop the icon"""
        if self.icon and self.running:
            self.running = False
            self.icon.stop()
