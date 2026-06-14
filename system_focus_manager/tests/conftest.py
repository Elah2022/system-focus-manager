"""
Shared pytest configuration.

Adds the project root (the folder that contains pin_manager.py, stats_manager.py,
etc.) to sys.path so the tests can `import pin_manager` without installing the
package. This keeps the tests in their own folder while still importing the
real modules.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
