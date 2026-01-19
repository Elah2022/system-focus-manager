"""
Browser Focus Controller Module
System Focus Manager extension to control Chromium-based browser tabs.
Supports: Chrome, Brave, Edge
"""

from .controller import (
    BrowserFocusController,
    BrowserFocusIntegration,
    get_chrome_launch_command
)

from .multi_browser import (
    BrowserDetector,
    MultiBrowserController,
    SUPPORTED_BROWSERS
)

__all__ = [
    'BrowserFocusController',
    'BrowserFocusIntegration',
    'get_chrome_launch_command',
    'BrowserDetector',
    'MultiBrowserController',
    'SUPPORTED_BROWSERS'
]
