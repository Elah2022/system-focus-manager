"""
System Focus Manager - My productivity tool
Here I start the entire system to manage my work modes

ORIGINAL AUTHOR: Manuela Riascos Hurtado
COPYRIGHT © 2025 Manuela Riascos Hurtado
EMAIL: manhurta54@gmail.com
GITHUB: https://github.com/Elah2022/system-focus-manager

This software is licensed under the MIT License.
Unauthorized removal of copyright notices is prohibited.
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from gui import FocusManagerGUI

# Import watermark verification
try:
    from _watermark import verify_watermark
    _WATERMARK = verify_watermark()
except ImportError:
    print("WARNING: Watermark verification failed. Copyright information may be missing.")
    _WATERMARK = None


def main():
    """Here I start the application"""
    # Verify copyright watermark
    if _WATERMARK:
        print(f"System Focus Manager v{_WATERMARK['version']}")
        print(f"© {_WATERMARK['copyright']}")
        print(f"Author: {_WATERMARK['author']}")
        print(f"GitHub: {_WATERMARK['github']}\n")

    # Get the PID of the launcher script to protect it from being closed
    launcher_pid = os.getpid()

    app = QApplication(sys.argv)
    window = FocusManagerGUI(launcher_pid=launcher_pid)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
