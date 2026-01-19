"""
Chrome Finder - Finds the correct Chrome path for debugging.
Helps the user select the correct executable.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict


class ChromeFinder:
    """Finds and validates Chrome paths"""

    COMMON_CHROME_PATHS = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        os.path.expandvars("C:/Users/%USERNAME%/AppData/Local/Google/Chrome/Application/chrome.exe"),
    ]

    @staticmethod
    def find_chrome() -> Optional[str]:
        """
        Finds the Chrome installation on the system.
        Returns the main executable path or None if not found.
        """
        for path in ChromeFinder.COMMON_CHROME_PATHS:
            if Path(path).exists():
                return path
        return None

    @staticmethod
    def is_valid_chrome_exe(path: str) -> Dict[str, any]:
        """
        Validates whether a path is the correct Chrome executable.

        Returns:
            {
                'valid': bool,
                'reason': str,
                'suggestion': Optional[str]
            }
        """
        if not path:
            return {
                'valid': False,
                'reason': 'Empty path',
                'suggestion': ChromeFinder.find_chrome()
            }

        path = os.path.expandvars(path)

        # Check that it exists
        if not Path(path).exists():
            return {
                'valid': False,
                'reason': f'File does not exist: {path}',
                'suggestion': ChromeFinder.find_chrome()
            }

        # Check that it is an .exe
        if not path.lower().endswith('.exe'):
            return {
                'valid': False,
                'reason': 'Not an executable file (.exe)',
                'suggestion': None
            }

        # Check that it is chrome.exe (not an updater or other executable)
        filename = Path(path).name.lower()
        if filename != 'chrome.exe':
            return {
                'valid': False,
                'reason': f'Not chrome.exe (it is: {filename})',
                'suggestion': ChromeFinder.find_chrome()
            }

        # Check that it is in the correct folder (Application)
        if 'Application' not in path:
            return {
                'valid': False,
                'reason': 'Chrome must be located inside the "Application" folder',
                'suggestion': ChromeFinder.find_chrome()
            }

        # All good!
        return {
            'valid': True,
            'reason': 'Valid Chrome path',
            'suggestion': None
        }

    @staticmethod
    def get_recommended_args_for_debugging() -> List[str]:
        """Returns recommended arguments for Chrome with debugging enabled"""
        return [
            "--remote-debugging-port=9222",
            f"--user-data-dir={os.path.expandvars('%LOCALAPPDATA%')}/ChromeDebugProfile"
        ]

    @staticmethod
    def create_chrome_config(custom_path: Optional[str] = None) -> Dict:
        """
        Creates a ready-to-use configuration for modes/*.json

        Args:
            custom_path: Custom path (optional, auto-detects if not provided)

        Returns:
            {
                'name': 'chrome',
                'path': 'C:/...',
                'args': [...]
            }
        """
        chrome_path = custom_path or ChromeFinder.find_chrome()

        if not chrome_path:
            raise FileNotFoundError("Chrome was not found on the system")

        # Validate the path
        validation = ChromeFinder.is_valid_chrome_exe(chrome_path)
        if not validation['valid']:
            if validation['suggestion']:
                chrome_path = validation['suggestion']
            else:
                raise ValueError(f"Invalid Chrome path: {validation['reason']}")

        return {
            'name': 'chrome',
            'path': chrome_path,
            'args': ChromeFinder.get_recommended_args_for_debugging()
        }


def validate_and_suggest(path: str) -> str:
    """
    Helper function: Validates a path and suggests a correction if needed.

    Args:
        path: Path provided by the user

    Returns:
        Validated path (may be the original or a suggested one)

    Raises:
        ValueError if the path is invalid and no suggestion is available
    """
    validation = ChromeFinder.is_valid_chrome_exe(path)

    if validation['valid']:
        return path

    if validation['suggestion']:
        print(f"⚠️ {validation['reason']}")
        print(f"✅ Using suggestion: {validation['suggestion']}")
        return validation['suggestion']

    raise ValueError(f"Invalid Chrome path: {validation['reason']}")


if __name__ == '__main__':
    # Test
    print("🔍 Searching for Chrome on the system...\n")

    chrome_path = ChromeFinder.find_chrome()
    if chrome_path:
        print(f"✅ Chrome found:")
        print(f"   {chrome_path}\n")

        # Create configuration
        config = ChromeFinder.create_chrome_config()
        print(f"📋 Recommended configuration:")
        print(f"   Path: {config['path']}")
        print(f"   Args: {config['args']}\n")

        # Validation test
        print("🧪 Validation test:")
        test_paths = [
            chrome_path,
            "C:/invalid/path/chrome.exe",
            "C:/Program Files/Google/Chrome/chrome_updater.exe"
        ]

        for test_path in test_paths:
            result = ChromeFinder.is_valid_chrome_exe(test_path)
            status = "✅" if result['valid'] else "❌"
            print(f"{status} {test_path}")
            print(f"   {result['reason']}")
            if result['suggestion']:
                print(f"   Suggestion: {result['suggestion']}")
            print()
    else:
        print("❌ Chrome not found in common paths")
