"""
General application configuration manager
Saves preferences like language, theme, etc.
"""

import json
import os
from pathlib import Path


class SettingsManager:
    """Handles general application configuration"""

    def __init__(self):
        # Use LOCALAPPDATA for persistent storage
        app_data = os.path.expandvars('%LOCALAPPDATA%')
        self.settings_file = Path(app_data) / 'FocusManager' / 'settings.json'
        # Create directory if it doesn't exist
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self.load_settings()

    def load_settings(self):
        """Load configuration from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error cargando settings: {e}")

        # Default configuration
        return {
            'language': 'es',
            'theme': 'light',
            'version': '2.0'
        }

    def save_settings(self):
        """Save configuration to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error guardando settings: {e}")
            return False

    def get(self, key, default=None):
        """Get a configuration value"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a configuration value and save"""
        self.settings[key] = value
        return self.save_settings()

    def get_language(self):
        """Get the configured language"""
        return self.settings.get('language', 'es')

    def set_language(self, lang_code):
        """Set the language and save"""
        return self.set('language', lang_code)
