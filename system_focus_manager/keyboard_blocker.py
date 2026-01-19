"""
Keyboard shortcut blocking for Ultra Focus Mode.
Intercepts dangerous key combinations that allow escaping from the mode.
"""

import keyboard
from typing import Callable, Optional
from logger import FocusLogger


class KeyboardBlocker:
    """Block keyboard shortcuts when Ultra Focus Mode is active"""

    # Shortcuts that are blocked in Ultra Focus Mode
    BLOCKED_SHORTCUTS = [
        # Window/application switching
        'alt+tab',
        'alt+shift+tab',
        'win+tab',

        # Browser - new tabs/windows
        'ctrl+t',           # New tab
        'ctrl+n',           # New window
        'ctrl+shift+n',     # Incognito window
        'ctrl+w',           # Close tab
        'ctrl+shift+t',     # Reopen closed tab
        'ctrl+l',           # Address bar
        'alt+d',            # Address bar (alternative)
        'ctrl+k',           # Search
        'ctrl+e',           # Search (alternative)
        'ctrl+shift+i',     # DevTools
        'ctrl+shift+j',     # Console
        'f12',              # DevTools
        'ctrl+tab',         # Next tab
        'ctrl+shift+tab',   # Previous tab
        'ctrl+1', 'ctrl+2', 'ctrl+3', 'ctrl+4', 'ctrl+5',  # Switch to specific tab
        'ctrl+6', 'ctrl+7', 'ctrl+8', 'ctrl+9',
        'ctrl+shift+delete',  # Delete history

        # System
        'alt+f4',
        'win+d',
        'win+m',
        'win+l',
        'ctrl+shift+esc',
        'win+r',
        'win+x',
        'win+e',  # Explorer

        # Others
        'ctrl+shift+q',  # Close browser
        'alt+space',     # Window menu
    ]

    def __init__(self, logger: Optional[FocusLogger] = None, on_block_callback: Optional[Callable] = None):
        """
        Args:
            logger: Logger used to record blocked attempts
            on_block_callback: Function called when a shortcut is blocked
        """
        self.logger = logger
        self.on_block_callback = on_block_callback
        self.is_active = False
        self._hooks = []

    def activate(self):
        """Activate shortcut blocking"""
        if self.is_active:
            return

        if self.logger:
            self.logger.info(
                f"Activating keyboard shortcut blocking for {len(self.BLOCKED_SHORTCUTS)} shortcuts"
            )

        # Register hooks for each blocked shortcut
        for shortcut in self.BLOCKED_SHORTCUTS:
            try:
                hook = keyboard.add_hotkey(
                    shortcut,
                    self._on_blocked_key,
                    args=(shortcut,),
                    suppress=True
                )
                self._hooks.append(hook)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error registering hook for {shortcut}: {e}")

        self.is_active = True

    def deactivate(self):
        """Deactivate shortcut blocking"""
        if not self.is_active:
            return

        if self.logger:
            self.logger.info("Deactivating keyboard shortcut blocking")

        # Remove all hooks
        for hook in self._hooks:
            try:
                keyboard.remove_hotkey(hook)
            except:
                pass

        self._hooks.clear()
        self.is_active = False

    def _on_blocked_key(self, shortcut: str):
        """Callback when a blocked shortcut is pressed"""
        if self.logger:
            self.logger.warning(f"🚫 Shortcut blocked in Ultra Focus Mode: {shortcut}")

        # Call callback if it exists
        if self.on_block_callback:
            self.on_block_callback(shortcut)

    def __del__(self):
        """Cleanup on destruction"""
        self.deactivate()
