"""
Copyright © 2025 Manuela Riascos Hurtado
Original Author: Manuela Riascos Hurtado
Email: manhurta54@gmail.com
GitHub: https://github.com/Elah2022/system-focus-manager

Licensed under the MIT License.
Unauthorized removal of this copyright notice is prohibited.
"""



import subprocess
import os
from pathlib import Path
from typing import List, Dict


class ApplicationLauncher:
    """My app launcher that validates they exist before opening them"""

    def __init__(self, logger=None):
        self.logger = logger

    def expand_path(self, path: str) -> str:
        """
        Expand environment variables in paths.
        Example: C:/Users/%USERNAME%/... -> C:/Users/manhu/...
        """
        return os.path.expandvars(path)

    def is_valid_path(self, path: str) -> bool:
        """Verify if the path exists"""
        expanded_path = self.expand_path(path)
        return Path(expanded_path).exists()

    def launch_application(self, app_config: Dict) -> bool:
        """
        Open an application according to its configuration.

        app_config must have:
        - path: path to executable
        - args: list of arguments (optional)
        - name: app name (for logs)

        Returns True if opened successfully
        """
        try:
            path = self.expand_path(app_config.get('path', ''))
            args = app_config.get('args', [])
            name = app_config.get('name', 'Unknown')

            # Validate that file exists
            if not self.is_valid_path(path):
                if self.logger:
                    self.logger.warning(f"No se encontró la app: {name} en {path}")
                return False

            # Expand environment variables in arguments too
            expanded_args = [self.expand_path(arg) for arg in args]

            # Build command
            command = [path] + expanded_args

            # Open application without blocking
            subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            if self.logger:
                self.logger.info(f"Aplicación abierta: {name}")

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error abriendo {name}: {str(e)}")
            return False

    def launch_multiple_applications(self, apps_config: List[Dict]) -> Dict[str, bool]:
        """
        Open multiple applications.
        Returns dictionary with results {name: success}
        """
        results = {}
        for app_config in apps_config:
            name = app_config.get('name', 'Unknown')
            results[name] = self.launch_application(app_config)
        return results

    def find_common_applications(self) -> Dict[str, str]:
        """
        Find common paths of popular applications.
        Useful for auto-configuration.
        """
        common_paths = {
            # Navegadores
            'Chrome': [
                'C:/Program Files/Google/Chrome/Application/chrome.exe',
                'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
            ],
            'Brave': [
                'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe',
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe'),
            ],
            'Firefox': [
                'C:/Program Files/Mozilla Firefox/firefox.exe',
                'C:/Program Files (x86)/Mozilla Firefox/firefox.exe',
            ],
            'Edge': [
                'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
            ],
            'Opera': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Programs/Opera/opera.exe'),
            ],
            'Opera GX': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Programs/Opera GX/opera.exe'),
            ],

            # Desarrollo
            'VS Code': [
                'C:/Program Files/Microsoft VS Code/Code.exe',
                'C:/Program Files (x86)/Microsoft VS Code/Code.exe',
            ],
            'Visual Studio': [
                'C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/devenv.exe',
                'C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/Common7/IDE/devenv.exe',
            ],
            'PyCharm': [
                'C:/Program Files/JetBrains/PyCharm 2024.1/bin/pycharm64.exe',
                'C:/Program Files/JetBrains/PyCharm 2023.3/bin/pycharm64.exe',
            ],
            'IntelliJ IDEA': [
                'C:/Program Files/JetBrains/IntelliJ IDEA 2024.1/bin/idea64.exe',
            ],

            # Música y Streaming
            'Spotify': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Roaming/Spotify/Spotify.exe'),
            ],

            # Comunicación
            'Discord': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Discord/Update.exe'),
            ],
            'Slack': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/slack/slack.exe'),
            ],
            'Telegram': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Roaming/Telegram Desktop/Telegram.exe'),
            ],
            'WhatsApp': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/WhatsApp/WhatsApp.exe'),
            ],
            'Zoom': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Roaming/Zoom/bin/Zoom.exe'),
            ],
            'Skype': [
                'C:/Program Files/Microsoft/Skype for Desktop/Skype.exe',
                'C:/Program Files (x86)/Microsoft/Skype for Desktop/Skype.exe',
            ],
            'Teams': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Microsoft/Teams/current/Teams.exe'),
            ],

            # Gaming
            'Steam': [
                'C:/Program Files (x86)/Steam/steam.exe',
                'C:/Program Files/Steam/steam.exe',
            ],
            'Epic Games': [
                'C:/Program Files (x86)/Epic Games/Launcher/Portal/Binaries/Win32/EpicGamesLauncher.exe',
                'C:/Program Files (x86)/Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe',
            ],
            'EA App': [
                'C:/Program Files/Electronic Arts/EA Desktop/EA Desktop/EADesktop.exe',
            ],
            'Origin': [
                'C:/Program Files (x86)/Origin/Origin.exe',
            ],
            'Battle.net': [
                'C:/Program Files (x86)/Battle.net/Battle.net.exe',
            ],
            'Ubisoft Connect': [
                'C:/Program Files (x86)/Ubisoft/Ubisoft Game Launcher/UbisoftConnect.exe',
            ],
            'GOG Galaxy': [
                'C:/Program Files (x86)/GOG Galaxy/GalaxyClient.exe',
            ],

            # Productividad
            'Notion': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Programs/Notion/Notion.exe'),
            ],
            'Obsidian': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Obsidian/Obsidian.exe'),
            ],
            'Evernote': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Programs/Evernote/Evernote.exe'),
            ],
            'OneNote': [
                'C:/Program Files/Microsoft Office/root/Office16/ONENOTE.EXE',
            ],

            # Adobe
            'Photoshop': [
                'C:/Program Files/Adobe/Adobe Photoshop 2024/Photoshop.exe',
                'C:/Program Files/Adobe/Adobe Photoshop 2023/Photoshop.exe',
            ],
            'Illustrator': [
                'C:/Program Files/Adobe/Adobe Illustrator 2024/Support Files/Contents/Windows/Illustrator.exe',
                'C:/Program Files/Adobe/Adobe Illustrator 2023/Support Files/Contents/Windows/Illustrator.exe',
            ],
            'Premiere Pro': [
                'C:/Program Files/Adobe/Adobe Premiere Pro 2024/Adobe Premiere Pro.exe',
            ],
            'After Effects': [
                'C:/Program Files/Adobe/Adobe After Effects 2024/Support Files/AfterFX.exe',
            ],

            # Diseño 3D
            'Blender': [
                'C:/Program Files/Blender Foundation/Blender 4.0/blender.exe',
                'C:/Program Files/Blender Foundation/Blender 3.6/blender.exe',
            ],
            'Unity': [
                'C:/Program Files/Unity/Hub/Editor/2023.1.0f1/Editor/Unity.exe',
                'C:/Program Files/Unity/Hub/Editor/2022.3.0f1/Editor/Unity.exe',
            ],
            'Unreal Engine': [
                'C:/Program Files/Epic Games/UE_5.3/Engine/Binaries/Win64/UnrealEditor.exe',
            ],

            # Otros
            'Figma': [
                os.path.expandvars('C:/Users/%USERNAME%/AppData/Local/Figma/Figma.exe'),
            ],
            'VLC': [
                'C:/Program Files/VideoLAN/VLC/vlc.exe',
                'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe',
            ],
            'OBS Studio': [
                'C:/Program Files/obs-studio/bin/64bit/obs64.exe',
            ],
            'Audacity': [
                'C:/Program Files/Audacity/Audacity.exe',
            ]
        }

        found_apps = {}
        for app_name, paths in common_paths.items():
            for path in paths:
                if Path(path).exists():
                    found_apps[app_name] = path
                    break

        return found_apps
