"""
Copyright © 2025 Manuela Riascos Hurtado
Original Author: Manuela Riascos Hurtado
Email: manhurta54@gmail.com
GitHub: https://github.com/Elah2022/system-focus-manager

Licensed under the MIT License.
Unauthorized removal of this copyright notice is prohibited.
"""



import psutil
import os
from typing import List, Dict


class ProcessManager:
    """My process manager that safely closes applications"""

    # List of processes I will NEVER close (they are critical to the system)
    PROTECTED_PROCESSES = [
        # Critical Windows processes
        'system', 'registry', 'smss.exe', 'csrss.exe', 'wininit.exe',
        'services.exe', 'lsass.exe', 'svchost.exe', 'explorer.exe',
        'dwm.exe', 'winlogon.exe',

        # Python (to avoid closing the Focus Manager itself)
        'python.exe', 'pythonw.exe',

        # Additional system processes
        'taskmgr.exe', 'conhost.exe',

        # Terminals and shells (ALWAYS protected to avoid closing the program)
        'cmd.exe', 'powershell.exe', 'pwsh.exe', 'bash.exe', 'sh.exe', 'wsl.exe',
        'openconsole.exe', 'windowsterminal.exe', 'wt.exe',  # Windows Terminal
        'py.exe', 'pyw.exe',  # Python Launcher

        # Security and antivirus
        'msmpeng.exe', 'securityhealthservice.exe', 'antimalware service executable',
        'windows defender', 'antimalwareservice.exe',

        # Audio and graphics
        'audiodg.exe', 'nvcontainer.exe', 'nvdisplay.container.exe',
        'applicationframehost.exe', 'runtimebroker.exe',

        # Edge WebView (system component used by many apps)
        'msedgewebview2.exe',

        # Other critical system processes
        'fontdrvhost.exe', 'sihost.exe', 'ctfmon.exe', 'taskhostw.exe',
        'searchindexer.exe', 'searchhost.exe', 'startmenuexperiencehost.exe',
        'shellexperiencehost.exe', 'textinputhost.exe'
    ]

    def __init__(self, logger=None):
        self.logger = logger

    def get_running_processes(self) -> List[Dict]:
        """Get a list of running processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'exe': proc.info['exe']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def is_process_running(self, process_name: str) -> bool:
        """Check whether a process is currently running"""
        process_name = process_name.lower()
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() == process_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def is_browser_with_debugging(self, proc) -> bool:
        """
        Check if a browser process has remote debugging enabled.
        Looks for listening debugging ports:
        - Chrome: 9222
        - Brave: 9223
        - Edge: 9224
        """
        debugging_ports = [9222, 9223, 9224]

        try:
            connections = proc.connections()
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr.port in debugging_ports:
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        return False

    def is_chrome_with_debugging(self, proc) -> bool:
        """Compatibility wrapper"""
        return self.is_browser_with_debugging(proc)

    def close_process(self, process_name: str) -> bool:
        """
        Safely close a process.
        For browsers (chrome.exe, brave.exe, msedge.exe), only closes instances
        that have remote debugging enabled.

        Returns True if closed successfully, False otherwise.
        """
        # Ensure it is not a protected process
        if process_name.lower() in [p.lower() for p in self.PROTECTED_PROCESSES]:
            if self.logger:
                self.logger.warning(f"Attempt to close protected process: {process_name}")
            return False

        closed = False
        process_name_lower = process_name.lower()

        # Browsers with special handling
        browser_processes = ['chrome.exe', 'brave.exe', 'msedge.exe']

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name_lower:

                    # Special logic for browsers: only close those with debugging enabled
                    if process_name_lower in browser_processes:
                        if not self.is_browser_with_debugging(proc):
                            continue
                        else:
                            if self.logger:
                                self.logger.info(
                                    f"Closing {process_name} with debugging enabled (PID: {proc.pid})"
                                )

                    proc.terminate()      # Graceful termination
                    proc.wait(timeout=3)  # Wait up to 3 seconds

                    if self.logger:
                        self.logger.info(f"Process closed: {process_name}")
                    closed = True

            except psutil.TimeoutExpired:
                # Force close if it does not respond
                try:
                    proc.kill()
                    if self.logger:
                        self.logger.info(f"Process force-killed: {process_name}")
                    closed = True
                except:
                    pass

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error closing {process_name}: {str(e)}")

        return closed

    def close_multiple_processes(self, process_list: List[str]) -> Dict[str, bool]:
        """
        Close multiple processes.
        Returns a dictionary with results: {process_name: success}
        """
        results = {}
        for process_name in process_list:
            results[process_name] = self.close_process(process_name)
        return results

    def get_process_count(self, process_name: str) -> int:
        """Count how many instances of a process are running"""
        count = 0
        process_name_lower = process_name.lower()
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() == process_name_lower:
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return count

    def close_non_whitelisted_apps(self, allowed_apps: List[str], main_pid: int = None, additional_pids: List[int] = None, ultra_strict: bool = False) -> Dict[str, int]:
        """
        Close all applications that are NOT in the whitelist and NOT protected.
        Similar to the website whitelist system.

        Args:
            allowed_apps: List of allowed process names (e.g. ['chrome.exe', 'Code.exe'])
            main_pid: Main process PID to protect (if None, uses current PID)
            additional_pids: Additional PIDs to protect (e.g., launcher script PID)
            ultra_strict: If True, only protect CRITICAL system processes (for Ultra Focus mode)

        Returns:
            Dict with stats: {'closed': int, 'protected': int, 'allowed': int}
        """
        stats = {'closed': 0, 'protected': 0, 'allowed': 0}

        # Normalize lists to lowercase for comparison
        allowed_lower = [app.lower() for app in allowed_apps]

        # Use ultra strict mode for Ultra Focus: only close apps with visible windows
        if ultra_strict:
            # Get PIDs of processes with visible windows (user applications)
            pids_with_windows = set()
            try:
                import win32gui
                import win32process

                def enum_windows_callback(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd):
                        if win32gui.GetWindowText(hwnd):  # Has a title
                            try:
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                pids_with_windows.add(pid)
                            except:
                                pass
                    return True

                win32gui.EnumWindows(enum_windows_callback, None)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error enumerating windows: {e}")

            # Never close terminals/shells/python launchers AND critical Windows system processes
            never_close = [
                # Terminals and Python
                'cmd.exe', 'powershell.exe', 'pwsh.exe', 'bash.exe', 'sh.exe',
                'conhost.exe', 'python.exe', 'pythonw.exe', 'py.exe', 'pyw.exe', 'focusmanager.exe',

                # Recording tools (temporary exception)
                'recording toolbar.exe', 'recordingtoolbar.exe', 'obs64.exe', 'obs32.exe', 'obs.exe',
                'snippingtool.exe', 'screensketch.exe',  # Windows Snipping Tool and Snip & Sketch

                # Windows System UI and Infrastructure (have visible windows but are system processes)
                'sihost.exe',                    # Shell Infrastructure Host
                'ctfmon.exe',                    # Text Services Framework
                'searchhost.exe',                # Windows Search
                'startmenuexperiencehost.exe',   # Start Menu
                'shellexperiencehost.exe',       # Taskbar and Action Center
                'textinputhost.exe',             # Touch Keyboard and Handwriting Panel
                'runtimebroker.exe',             # Runtime Broker for Windows Store apps
                'applicationframehost.exe',      # Universal Windows Platform (UWP) app host
                'widgetservice.exe',             # Windows Widgets Service
                'widgets.exe',                   # Windows Widgets
                'shellhost.exe',                 # Shell Host
                'dllhost.exe',                   # COM Surrogate
                'msedgewebview2.exe',            # Edge WebView2 Runtime (system component)
                'backgroundtaskhost.exe',        # Background Task Host
                'crossdeviceresume.exe',         # Cross Device Resume
                'smartscreen.exe',               # Windows SmartScreen
                'windowspackagemanagerserver.exe',  # Package Manager
                'useroobebroker.exe',            # Out Of Box Experience Broker
            ]
            protected_lower = [proc.lower() for proc in never_close]
        else:
            pids_with_windows = None
            protected_lower = [proc.lower() for proc in self.PROTECTED_PROCESSES]

        # Get current process and parent PIDs (to avoid closing the app itself or its terminal)
        protected_pids = set()

        # Helper function to protect a PID and all its parents
        def protect_pid_chain(pid_to_protect, label="main"):
            try:
                current = psutil.Process(pid_to_protect)
                protected_pids.add(current.pid)

                if self.logger:
                    self.logger.info(f"Protecting {label} PID: {current.pid} ({current.name()})")

                # ALWAYS log to file even if logger doesn't exist (for debugging)
                import sys
                print(f"[DEBUG] Protecting {label} PID: {current.pid} ({current.name()})", file=sys.stderr)

                # Protect all parent processes (terminal, shell, etc.)
                parent_count = 0
                while True:
                    try:
                        parent = current.parent()
                        if parent is None:
                            break
                        protected_pids.add(parent.pid)
                        if self.logger:
                            self.logger.info(
                                f"  Protecting {label} parent #{parent_count + 1}: "
                                f"PID {parent.pid} ({parent.name()})"
                            )
                        current = parent
                        parent_count += 1
                        if parent_count > 20:  # Safety limit
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error retrieving protected PIDs for {label}: {e}")

        # Protect main PID chain
        try:
            pid_to_protect = main_pid if main_pid is not None else os.getpid()
            protect_pid_chain(pid_to_protect, "main")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error retrieving main protected PIDs: {e}")

        # Protect additional PIDs (e.g., launcher script)
        if additional_pids:
            for idx, additional_pid in enumerate(additional_pids):
                if additional_pid is not None:
                    protect_pid_chain(additional_pid, f"launcher#{idx+1}")

        # In ultra_strict mode, also protect ALL cmd.exe and conhost.exe processes
        # (these might not be in the parent chain but should never be closed)
        if ultra_strict:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name_lower = proc.info['name'].lower()
                    if proc_name_lower in ['cmd.exe', 'conhost.exe', 'openconsole.exe', 'windowsterminal.exe', 'wt.exe']:
                        protected_pids.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if self.logger:
            self.logger.info(f"Total protected PIDs: {len(protected_pids)}")

        # Iterate over all processes
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name']
                proc_name_lower = proc_name.lower()
                proc_pid = proc.info['pid']

                # Check if it is the current process or one of its parents (HIGHEST PRIORITY)
                if proc_pid in protected_pids:
                    stats['protected'] += 1
                    continue

                # Check if it is protected by name (MUST BE BEFORE window check)
                if proc_name_lower in protected_lower:
                    stats['protected'] += 1
                    continue

                # Check if it is whitelisted
                if proc_name_lower in allowed_lower:
                    # Special handling for browsers: only allow debug instances
                    browser_processes = ['chrome.exe', 'brave.exe', 'msedge.exe']

                    if proc_name_lower in browser_processes:
                        # Check if this browser has debugging enabled
                        try:
                            cmdline = proc.cmdline()
                            cmdline_str = ' '.join(cmdline).lower()

                            if '--remote-debugging-port' in cmdline_str:
                                # Debug browser → ALLOW
                                stats['allowed'] += 1
                                continue
                            else:
                                # Normal browser (no debugging) → CLOSE IT
                                # This allows debug browser but closes normal instances
                                if self.logger:
                                    self.logger.warning(
                                        f"🚫 Closing normal {proc_name} (no debugging) - "
                                        f"Only debug instances allowed (PID: {proc.pid})"
                                    )
                                # Don't continue, let it fall through to closure
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Can't check cmdline, allow it to be safe
                            stats['allowed'] += 1
                            continue
                    else:
                        # Non-browser app in whitelist → allow normally
                        stats['allowed'] += 1
                        continue

                # In ultra strict mode, ONLY close if it has a visible window
                if ultra_strict and pids_with_windows is not None:
                    if proc_pid not in pids_with_windows:
                        # Process has no window, skip it (it's a background service)
                        stats['protected'] += 1
                        continue

                # Not protected and not allowed → close it
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                    stats['closed'] += 1
                    if self.logger:
                        self.logger.info(
                            f"Non-whitelisted app closed: {proc_name} (PID: {proc.pid})"
                        )
                except psutil.TimeoutExpired:
                    try:
                        proc.kill()
                        stats['closed'] += 1
                        if self.logger:
                            self.logger.info(
                                f"App force-killed: {proc_name} (PID: {proc.pid})"
                            )
                    except:
                        pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error processing process: {str(e)}")

        return stats
