"""
Browser Focus Controller
Controls which tabs are allowed in Chrome when a mode is active.
Uses Chrome Remote Debugging API (local, no hacking).
"""

import requests
import json
import time
from typing import List, Optional, Dict
from urllib.parse import urlparse


class BrowserFocusController:
    """Browser tab controller using Chrome Remote Debugging"""

    def __init__(self, debugging_port: int = 9222, logger=None):
        self.debugging_port = debugging_port
        self.base_url = f"http://localhost:{debugging_port}"
        self.allowed_domains: List[str] = []
        self.strict_mode = False
        self.monitoring = False
        self.logger = logger  # Optional logger for debugging

        # Ultra Focus Mode
        self.ultra_focus_active = False
        self.ultra_focus_locked_domain: Optional[str] = None
        self.ultra_focus_settings = {}

    def is_chrome_debugging_available(self) -> bool:
        """Checks if Chrome is running with remote debugging enabled"""
        try:
            response = requests.get(f"{self.base_url}/json", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_open_tabs(self) -> List[Dict]:
        """Gets list of all open tabs"""
        try:
            response = requests.get(f"{self.base_url}/json", timeout=2)
            if response.status_code == 200:
                tabs = response.json()
                # Filter only pages (not extensions, devtools, etc)
                return [tab for tab in tabs if tab.get('type') == 'page']
            return []
        except requests.exceptions.RequestException as e:
            return []

    def close_tab(self, tab_id: str) -> bool:
        """Closes a specific tab by its ID"""
        try:
            response = requests.get(f"{self.base_url}/json/close/{tab_id}", timeout=2)
            return response.status_code == 200
        except requests.exceptions.Timeout:
            # Timeout is common when closing many tabs quickly
            if self.logger:
                self.logger.debug(f"Timeout closing tab {tab_id[:8]}... (browser busy)")
            return False
        except requests.exceptions.RequestException as e:
            # Only show serious errors
            if self.logger:
                self.logger.debug(f"Error closing tab: {type(e).__name__}")
            return False

    def open_new_tab(self, url: str) -> bool:
        """Opens a new tab with the specified URL"""
        try:
            # Chrome DevTools Protocol: PUT /json/new with URL in body
            # Alternative: GET /json/new?{url} (direct URL without param name)
            response = requests.put(f"{self.base_url}/json/new", data=url, timeout=2)
            if response.status_code == 200:
                return True

            # Fallback: try GET with URL as query string (some browsers)
            response = requests.get(f"{self.base_url}/json/new?{url}", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            return False

    def is_domain_allowed(self, url: str) -> bool:
        """Checks if a domain is in the whitelist"""
        if not self.allowed_domains:
            return True  # If no whitelist, allow everything

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. if it exists
            if domain.startswith('www.'):
                domain = domain[4:]

            # Check against each allowed domain
            for allowed in self.allowed_domains:
                allowed_clean = allowed.lower().replace('www.', '')

                # Allow subdomains
                if domain == allowed_clean or domain.endswith('.' + allowed_clean):
                    return True

            return False
        except Exception as e:
            return True

    def scan_and_enforce(self) -> Dict[str, int]:
        """
        Scans open tabs and closes those that are not allowed.
        Returns operation statistics.
        """
        stats = {
            'total_tabs': 0,
            'blocked_tabs': 0,
            'allowed_tabs': 0
        }

        if not self.is_chrome_debugging_available():
            return stats

        tabs = self.get_open_tabs()
        stats['total_tabs'] = len(tabs)

        # First, identify which tabs will be blocked
        tabs_to_block = []
        allowed_count = 0

        for tab in tabs:
            url = tab.get('url', '')
            tab_id = tab.get('id')
            title = tab.get('title', 'Untitled')

            if not tab_id:
                continue

            # Ignore Chrome/Edge special pages
            if url.startswith('chrome://') or url.startswith('chrome-extension://') or url.startswith('edge://'):
                continue

            if self.is_domain_allowed(url):
                allowed_count += 1
            else:
                tabs_to_block.append({'id': tab_id, 'title': title, 'url': url})

        stats['allowed_tabs'] = allowed_count

        # If ALL tabs will be blocked and there's a whitelist, open an allowed one first
        if allowed_count == 0 and len(tabs_to_block) > 0 and len(self.allowed_domains) > 0:
            first_domain = self.allowed_domains[0]
            url = f"https://{first_domain}"
            if self.open_new_tab(url):
                # Wait a moment for the tab to open
                import time
                time.sleep(1)

        # Now actually close the blocked tabs
        for tab in tabs_to_block:
            msg = f"Blocking tab: {tab['title']} ({tab['url']})"
            if self.logger:
                self.logger.warning(msg)
            if self.close_tab(tab['id']):
                stats['blocked_tabs'] += 1

        return stats

    def set_whitelist(self, domains: List[str]):
        """Configures the whitelist of allowed domains"""
        self.allowed_domains = domains
        if self.logger:
            self.logger.info(f"Whitelist configured: {', '.join(domains)}")

    def clear_whitelist(self):
        """Clears the whitelist (allows all domains)"""
        self.allowed_domains = []

    def start_monitoring(self, interval_seconds: int = 10) -> bool:
        """
        Starts continuous tab monitoring (strict mode).
        NOTE: This function blocks. Must be run in a separate thread.
        """
        if not self.is_chrome_debugging_available():
            return False

        self.monitoring = True

        while self.monitoring:
            stats = self.scan_and_enforce()
            time.sleep(interval_seconds)

        return True

    def stop_monitoring(self):
        """Stops continuous monitoring"""
        self.monitoring = False

    # ===== ULTRA FOCUS MODE =====

    def activate_ultra_focus(self, settings: Dict) -> bool:
        """
        Activates Ultra Focus Mode - locks to the current domain.

        Args:
            settings: Ultra focus configuration (lock_to_current_domain, etc.)

        Returns:
            True if activated successfully
        """
        # Get the domain of the current active tab
        tabs = self.get_open_tabs()
        if not tabs:
            if self.logger:
                self.logger.error("No tabs open to lock in Ultra Focus")
            return False

        # Use the first tab as the locked domain
        current_tab = tabs[0]
        current_url = current_tab.get('url', '')

        try:
            parsed = urlparse(current_url)
            locked_domain = parsed.netloc.lower()

            if locked_domain.startswith('www.'):
                locked_domain = locked_domain[4:]

            self.ultra_focus_locked_domain = locked_domain
            self.ultra_focus_settings = settings
            self.ultra_focus_active = True

            if self.logger:
                self.logger.info(f"🔒 Ultra Focus activated - locked domain: {locked_domain}")

            # Close all tabs that are NOT from the locked domain
            self._enforce_ultra_focus_lockdown()

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error activating Ultra Focus: {e}")
            return False

    def activate_ultra_focus_with_domain(self, settings: Dict, locked_domain: str) -> bool:
        """
        Activates Ultra Focus Mode with a specific domain.

        Args:
            settings: Ultra focus configuration
            locked_domain: Domain to lock to (e.g., 'canvas.instructure.com')

        Returns:
            True if activated successfully
        """
        if not locked_domain:
            if self.logger:
                self.logger.error("No domain specified for Ultra Focus")
            return False

        try:
            # Clean the domain
            locked_domain = locked_domain.lower().strip()
            if locked_domain.startswith('www.'):
                locked_domain = locked_domain[4:]

            self.ultra_focus_locked_domain = locked_domain
            self.ultra_focus_settings = settings
            self.ultra_focus_active = True

            if self.logger:
                self.logger.info(f"🔒 Ultra Focus activated - specified domain: {locked_domain}")

            # Close all tabs that are NOT from the locked domain
            self._enforce_ultra_focus_lockdown()

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error activating Ultra Focus with domain: {e}")
            return False

    def deactivate_ultra_focus(self):
        """Deactivates Ultra Focus Mode"""
        if self.ultra_focus_active:
            if self.logger:
                self.logger.info("🔓 Ultra Focus deactivated")

        self.ultra_focus_active = False
        self.ultra_focus_locked_domain = None
        self.ultra_focus_settings = {}

    def set_fullscreen(self, force: bool = False) -> bool:
        """
        Sets the browser to fullscreen mode using win32api

        Args:
            force: If True, sends F11 always. If False, only if not in fullscreen
        """
        try:
            import win32gui
            import win32con
            import time

            # Find the browser window
            browser_names = ['Chrome', 'Brave', 'Edge', 'Microsoft Edge']
            window_handle = None

            def enum_windows_callback(hwnd, result):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    for browser_name in browser_names:
                        if browser_name.lower() in title.lower():
                            result.append(hwnd)

            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)

            if windows:
                window_handle = windows[0]  # Take the first browser window

                # Check if already in fullscreen (only if not force)
                if not force:
                    # Get window info
                    placement = win32gui.GetWindowPlacement(window_handle)
                    # If showCmd == 3 (SW_SHOWMAXIMIZED), might be in fullscreen
                    # But there's no direct way, so just send F11 the first time
                    if hasattr(self, '_fullscreen_applied') and self._fullscreen_applied:
                        return True  # Already applied F11, don't do it again

                # Activate the window
                win32gui.SetForegroundWindow(window_handle)
                time.sleep(0.2)

                # Send F11 using SendInput
                import win32api
                VK_F11 = 0x7A

                # Press F11
                win32api.keybd_event(VK_F11, 0, 0, 0)
                time.sleep(0.05)
                # Release F11
                win32api.keybd_event(VK_F11, 0, win32con.KEYEVENTF_KEYUP, 0)

                # Mark that we've applied F11
                self._fullscreen_applied = True

                if self.logger:
                    self.logger.info("🖥️ Browser in fullscreen (F11)")
                return True
            else:
                if self.logger:
                    self.logger.warning("Browser window not found for fullscreen")
                return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error setting browser to fullscreen: {e}")
            return False

    def _enforce_ultra_focus_lockdown(self) -> Dict[str, int]:
        """
        Enforces lockdown in Ultra Focus.
        Closes ALL tabs that are not from the locked domain.
        """
        stats = {'blocked': 0, 'kept': 0}

        if not self.ultra_focus_active or not self.ultra_focus_locked_domain:
            return stats

        tabs = self.get_open_tabs()
        allow_subdomain_nav = self.ultra_focus_settings.get('allow_subdomain_navigation', True)

        for tab in tabs:
            url = tab.get('url', '')

            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()

                if domain.startswith('www.'):
                    domain = domain[4:]

                # Check if the tab is from the locked domain
                is_locked_domain = False

                if allow_subdomain_nav:
                    # Allow subdomains
                    is_locked_domain = (domain == self.ultra_focus_locked_domain or
                                        domain.endswith('.' + self.ultra_focus_locked_domain))
                else:
                    # Only exact domain
                    is_locked_domain = (domain == self.ultra_focus_locked_domain)

                if is_locked_domain:
                    stats['kept'] += 1
                else:
                    # NOT from the locked domain -> REDIRECT back
                    if self.logger:
                        self.logger.warning(f"🚫 Ultra Focus: Redirecting from {domain} to {self.ultra_focus_locked_domain}")

                    # Redirect to the allowed domain page using CDP
                    redirect_url = f"https://{self.ultra_focus_locked_domain}"
                    try:
                        import requests
                        import json

                        # Get WebSocket URL of the tab
                        ws_url = tab.get('webSocketDebuggerUrl')
                        if ws_url:
                            # Use WebSocket to send navigation command
                            import websocket
                            ws = websocket.create_connection(ws_url)

                            # Send Page.navigate command
                            navigate_command = {
                                "id": 1,
                                "method": "Page.navigate",
                                "params": {"url": redirect_url}
                            }
                            ws.send(json.dumps(navigate_command))
                            ws.close()

                            if self.logger:
                                self.logger.info(f"✅ Tab redirected to {redirect_url}")
                        else:
                            # Fallback: use activation endpoint + navigation
                            tab_id = tab['id']
                            requests.get(f"{self.base_url}/json/activate/{tab_id}", timeout=1)
                            # Note: We can't navigate directly without WebSocket,
                            # but at least we activate the correct tab
                            if self.logger:
                                self.logger.warning(f"⚠️ Could not redirect automatically (no WebSocket)")

                        stats['blocked'] += 1
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error redirecting tab: {e}")
                        # If all fails, try to close and open new tab
                        try:
                            self.close_tab(tab['id'])
                            self.open_new_tab(redirect_url)
                        except:
                            pass

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error processing tab in Ultra Focus: {e}")

        return stats

    def is_ultra_focus_active(self) -> bool:
        """Returns if Ultra Focus is active"""
        return self.ultra_focus_active


class BrowserFocusIntegration:
    """
    Integration with System Focus Manager.
    Handles the logic of which whitelist to apply according to the mode.
    """

    def __init__(self, controller: BrowserFocusController):
        self.controller = controller
        self.mode_rules: Dict[str, List[str]] = {}

    def load_rules(self, rules_path: str):
        """Loads whitelist rules from JSON"""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.mode_rules = data.get('mode_whitelists', {})
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as e:
            pass

    def activate_mode(self, mode_name: str) -> bool:
        """
        Activates browser restrictions for a specific mode.
        Returns True if rules were found for the mode.
        """
        mode_name_lower = mode_name.lower()

        if mode_name_lower in self.mode_rules:
            whitelist = self.mode_rules[mode_name_lower]
            self.controller.set_whitelist(whitelist)

            # Scan and close tabs immediately
            # (scan_and_enforce already handles opening a tab if needed)
            stats = self.controller.scan_and_enforce()

            return True
        else:
            return False

    def deactivate(self):
        """Deactivates restrictions (allows all domains)"""
        self.controller.clear_whitelist()


# Helper function to start Chrome with debugging
def get_chrome_launch_command(debugging_port: int = 9222) -> str:
    """
    Returns the command to start Chrome with remote debugging.
    The user must execute this BEFORE using the controller.
    """
    return f'"C:/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port={debugging_port}'


if __name__ == '__main__':
    # Basic test
    print("Testing Browser Focus Controller...")

    controller = BrowserFocusController()

    if controller.is_chrome_debugging_available():
        print("Chrome debugging available")

        # Test: get tabs
        tabs = controller.get_open_tabs()
        print(f"Open tabs: {len(tabs)}")

        for tab in tabs[:3]:  # Show first 3
            print(f"  - {tab.get('title', 'Untitled')}")
            print(f"    {tab.get('url', 'No URL')}")
    else:
        print("Chrome is not running with debugging enabled")
        print(f"\nTo enable it, run:")
        print(get_chrome_launch_command())