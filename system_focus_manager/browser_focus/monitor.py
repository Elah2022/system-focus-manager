"""
Background Monitor for Browser Focus Controller.
Runs continuous monitoring in a separate thread.
"""

import threading
from typing import Optional, Callable
from .controller import BrowserFocusController


class BrowserMonitorThread:
    """Thread that monitors browser tabs in the background"""

    def __init__(self, controller: BrowserFocusController, interval: int = 10):
        self.controller = controller
        self.interval = interval
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.on_block_callback: Optional[Callable[[str, str], None]] = None
        self.on_browser_closed_callback: Optional[Callable[[], None]] = None
        self.protected_urls = []  # URLs recently restored (ignored by the monitor)
        self.browser_was_available = False  # Track if browser was previously available

    def start(self):
        """Starts background monitoring"""
        if self.running:
            print("Monitor is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print(f"Browser monitor started (every {self.interval}s)")

    def stop(self):
        """Stops monitoring"""
        if not self.running:
            return

        self.running = False
        self.controller.stop_monitoring()

        if self.thread:
            self.thread.join(timeout=2)

        print("Browser monitor stopped")

    def set_block_callback(self, callback: Callable[[str, str], None]):
        """
        Sets a callback that is called when a tab is blocked.
        callback(url, title) -> None
        """
        self.on_block_callback = callback

    def set_browser_closed_callback(self, callback: Callable[[], None]):
        """
        Sets a callback that is called when the browser is closed in Ultra Focus.
        callback() -> None
        """
        self.on_browser_closed_callback = callback

    def set_protected_urls(self, urls: list):
        """
        Sets a list of protected URLs that the monitor should NOT close.
        Used for tabs recently restored by Pomodoro.
        """
        self.protected_urls = urls

    def _monitor_loop(self):
        """Monitoring loop (runs in a separate thread)"""
        import time

        while self.running:
            browser_available = self.controller.is_chrome_debugging_available()

            # Detect browser closure (both Focus and Ultra Focus modes)
            if not browser_available and self.browser_was_available:
                # Browser was closed! Call callback to reopen it
                if self.controller.is_ultra_focus_active():
                    print("⚠️ Ultra Focus: Browser closed! Attempting to reopen...")
                else:
                    print("⚠️ Focus: Browser closed! Attempting to reopen...")

                if self.on_browser_closed_callback:
                    try:
                        self.on_browser_closed_callback()
                    except Exception as e:
                        print(f"Error reopening browser: {e}")

            # Update availability status
            self.browser_was_available = browser_available

            if not browser_available:
                time.sleep(self.interval)
                continue

            # If Ultra Focus is active, enforce lockdown
            if self.controller.is_ultra_focus_active():
                self.controller._enforce_ultra_focus_lockdown()
            else:
                # Normal whitelist monitoring
                tabs = self.controller.get_open_tabs()

                for tab in tabs:
                    if not self.running:
                        break

                    url = tab.get('url', '')
                    tab_id = tab.get('id')
                    title = tab.get('title', 'Untitled')

                    # Ignore special Chrome / Edge / Brave pages
                    if (
                        url.startswith('chrome://')
                        or url.startswith('chrome-extension://')
                        or url.startswith('edge://')
                        or url.startswith('brave://')
                    ):
                        continue

                    # Ignore protected URLs (recently restored from Pomodoro)
                    is_protected = False
                    for protected_url in self.protected_urls:
                        if protected_url in url or url in protected_url:
                            is_protected = True
                            break

                    if is_protected:
                        continue  # Skip protected URLs

                    # Check if domain is allowed
                    if not self.controller.is_domain_allowed(url):
                        print(f"Blocking tab: {title}")

                        # Close disallowed tab
                        if self.controller.close_tab(tab_id):
                            # Call callback if it exists
                            if self.on_block_callback:
                                try:
                                    self.on_block_callback(url, title)
                                except Exception as e:
                                    print(f"Callback error: {e}")

            time.sleep(self.interval)


if __name__ == '__main__':
    # Monitor test
    from pathlib import Path

    controller = BrowserFocusController()

    if not controller.is_chrome_debugging_available():
        print("Chrome not available. Start Chrome with:")
        print('"C:/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9222')
        exit(1)

    # Test whitelist
    controller.set_whitelist([
        "google.com",
        "stackoverflow.com",
        "github.com"
    ])

    # Example callback
    def on_block(url, title):
        print(f"BLOCKED: {title} ({url})")

    # Start monitor
    monitor = BrowserMonitorThread(controller, interval=5)
    monitor.set_block_callback(on_block)
    monitor.start()

    print("\nMonitor running. Press Ctrl+C to stop...")
    print("Try opening disallowed tabs to test blocking\n")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
        print("Test completed")
