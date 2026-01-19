"""
Multi-Browser Support
Detects and controls Chrome, Brave, Edge, and other Chromium-based browsers
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

# Supported browser configuration
SUPPORTED_BROWSERS = {
    'chrome': {
        'name': 'Google Chrome',
        'exe_name': 'chrome.exe',
        'default_paths': [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        ],
        'port': 9222,
        'user_data_dir_name': 'ChromeDebugProfile',
        'icon': 'Chrome'
    },
    'brave': {
        'name': 'Brave Browser',
        'exe_name': 'brave.exe',
        'default_paths': [
            r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
            r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe',
        ],
        'port': 9223,
        'user_data_dir_name': 'BraveDebugProfile',
        'icon': 'Brave'
    },
    'edge': {
        'name': 'Microsoft Edge',
        'exe_name': 'msedge.exe',
        'default_paths': [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        ],
        'port': 9224,
        'user_data_dir_name': 'EdgeDebugProfile',
        'icon': 'Edge'
    }
}


class BrowserDetector:
    """Detects browsers installed on the system"""

    @staticmethod
    def find_browser(browser_key: str) -> Optional[str]:
        """
        Searches for a specific browser on the system.
        Returns the path if found, None otherwise.
        """
        if browser_key not in SUPPORTED_BROWSERS:
            return None

        config = SUPPORTED_BROWSERS[browser_key]

        # Search default paths
        for path in config['default_paths']:
            if os.path.exists(path):
                return path

        return None

    @staticmethod
    def find_all_browsers() -> Dict[str, str]:
        """
        Searches for all supported browsers.
        Returns dict: {browser_key: path}
        """
        found = {}
        for browser_key in SUPPORTED_BROWSERS.keys():
            path = BrowserDetector.find_browser(browser_key)
            if path:
                found[browser_key] = path
        return found

    @staticmethod
    def get_browser_config(browser_key: str) -> Optional[Dict]:
        """Returns the configuration for a browser"""
        return SUPPORTED_BROWSERS.get(browser_key)

    @staticmethod
    def is_valid_browser_exe(path: str, browser_key: str) -> bool:
        """Checks whether a path is a valid executable for a specific browser"""
        if not os.path.exists(path):
            return False

        config = SUPPORTED_BROWSERS.get(browser_key)
        if not config:
            return False

        # Verify correct executable name
        exe_name = os.path.basename(path).lower()
        return exe_name == config['exe_name'].lower()

    @staticmethod
    def get_recommended_args(browser_key: str) -> List[str]:
        """
        Returns recommended debugging arguments for a browser.
        Output is a list of arguments for subprocess.
        """
        config = SUPPORTED_BROWSERS.get(browser_key)
        if not config:
            return []

        # Get user data directory (expand LOCALAPPDATA)
        localappdata = os.environ.get('LOCALAPPDATA', '')
        user_data_dir = os.path.join(localappdata, config['user_data_dir_name'])

        return [
            f"--remote-debugging-port={config['port']}",
            f"--user-data-dir={user_data_dir}",
            "--remote-allow-origins=*"
        ]

    @staticmethod
    def create_browser_app_config(browser_key: str, custom_path: Optional[str] = None) -> Optional[Dict]:
        """
        Creates the full configuration to add a browser to the app list.
        Returns dict formatted for modes/*.json
        """
        config = SUPPORTED_BROWSERS.get(browser_key)
        if not config:
            return None

        # Use custom path or auto-detect
        path = custom_path or BrowserDetector.find_browser(browser_key)
        if not path:
            return None

        args = BrowserDetector.get_recommended_args(browser_key)

        return {
            'name': browser_key,
            'path': path,
            'args': args
        }

    @staticmethod
    def get_port_for_browser(browser_key: str) -> int:
        """Returns the debugging port for a browser"""
        config = SUPPORTED_BROWSERS.get(browser_key)
        return config['port'] if config else 9222


class MultiBrowserController:
    """
    Controller that manages multiple browsers simultaneously.
    Allows applying whitelists to Chrome, Brave, and Edge at the same time.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.controllers = {}  # {browser_key: BrowserFocusController}

    def add_browser(self, browser_key: str):
        """
        Adds a browser to multi-browser control.
        Only works if the browser is running with remote debugging enabled.
        """
        from .controller import BrowserFocusController

        port = BrowserDetector.get_port_for_browser(browser_key)
        controller = BrowserFocusController(debugging_port=port, logger=self.logger)

        # Only add if available
        if controller.is_chrome_debugging_available():
            self.controllers[browser_key] = controller
            if self.logger:
                self.logger.info(f"Browser {browser_key} added to control (port {port})")
            return True
        else:
            if self.logger:
                self.logger.warning(f"Browser {browser_key} not available on port {port}")
            return False

    def remove_browser(self, browser_key: str):
        """Removes a browser from control"""
        if browser_key in self.controllers:
            del self.controllers[browser_key]

    def set_whitelist_all(self, domains: List[str]):
        """Applies the same whitelist to all controlled browsers"""
        for browser_key, controller in self.controllers.items():
            controller.set_whitelist(domains)
            if self.logger:
                self.logger.info(f"Whitelist applied to {browser_key}")

    def clear_whitelist_all(self):
        """Clears the whitelist from all browsers"""
        for controller in self.controllers.values():
            controller.clear_whitelist()

    def scan_and_enforce_all(self) -> Dict[str, Dict]:
        """
        Scans and enforces rules on all browsers.
        Returns: {browser_key: stats}
        """
        results = {}
        for browser_key, controller in self.controllers.items():
            if controller.is_chrome_debugging_available():
                stats = controller.scan_and_enforce()
                results[browser_key] = stats
        return results

    def get_active_browsers(self) -> List[str]:
        """Returns a list of browsers currently under control"""
        return list(self.controllers.keys())


if __name__ == '__main__':
    # Detection test
    print("Detecting installed browsers...")

    found = BrowserDetector.find_all_browsers()

    if not found:
        print("No supported browsers found")
    else:
        print(f"\nBrowsers found: {len(found)}")
        for browser_key, path in found.items():
            config = BrowserDetector.get_browser_config(browser_key)
            print(f"  {config['icon']} {config['name']}")
            print(f"     Path: {path}")
            print(f"     Port: {config['port']}")

            # Show recommended arguments
            args = BrowserDetector.get_recommended_args(browser_key)
            print(f"     Args: {' '.join(args)}\n")
