# ⚡ Focus Manager

> **Advanced productivity application with process control and browser domain locking for Windows**

A powerful desktop application built with Python and PySide6 that helps you maintain focus by blocking distractions, managing applications, and enforcing time-based work sessions.

---

## 🎯 Features

### 🔐 **Ultra Focus Mode**
Maximum concentration mode with extreme restrictions:
- Lock browser to a single domain (any other site is redirected back)
- Automatic closure of unauthorized applications, including Task Manager at the same privilege level
- Browser forced into fullscreen
- Only one selected browser allowed (Chrome/Brave/Edge)
- PIN-protected exit; any forced closure is recorded in a tamper-evident audit log

### 🎯 **Focus Mode**
Balanced productivity mode:
- Block distracting applications
- Control which apps can run (whitelist)
- Monitor and enforce browser restrictions
- Customizable application rules

### 🍅 **Pomodoro Timer**
Built-in Pomodoro technique support:
- Configurable work/break intervals (default: 25min work / 5min break)
- Multiple cycles with automatic transitions
- Visual and notification alerts
- Auto-deactivates mode after completion

### ⏱️ **Session Timer**
- Set time limits for focus sessions
- Automatic mode deactivation when time expires
- Real-time countdown display

### 👨‍👩‍👧 **Parental Controls**
- PIN-protected settings and mode changes
- Prevent unauthorized deactivation
- Secure PIN storage with hashing

---

## 🚀 Installation

### From Release (Recommended)

1. Download the latest `focus-manager.exe` from [Releases](https://github.com/YOUR-USERNAME/focus-manager/releases)
2. Run the executable
3. Grant necessary permissions when prompted

> **Note:** Windows Defender may flag the executable. Click "More info" → "Run anyway" to proceed.

### From Source

```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/focus-manager.git
cd focus-manager

# Install dependencies
pip install -r requirements.txt

# Run the application
cd system_focus_manager
python main.py
```

**Prerequisites:**
- Windows 10/11
- Python 3.8+ (if running from source)

---

## 📖 Usage

### Quick Start

1. **Launch the application**
2. **Configure a mode** - Click "⚙️ Configure" on Focus or Ultra Focus
3. **Activate** - Click "▶️ Activate"
4. **Stay focused** - The app enforces your rules automatically
5. **Use timers** - Pomodoro or simple countdown
6. **Deactivate** - Click "■ Deactivate" (PIN may be required)

### Ultra Focus Mode Setup

1. Click "⚙️ Configure" on Ultra Focus
2. Enter domain to lock (e.g., `github.com`)
3. Select browser (Chrome/Brave/Edge)
4. Save and activate
5. You can only browse that specific domain

### PIN Protection

1. Click "PIN Settings"
2. Create 4-digit PIN
3. Enable Parental Mode (optional)
4. PIN required to deactivate/modify settings

---

## 🏗️ Architecture

**Technology Stack:**
- GUI: PySide6 (Qt6)
- Browser Control: Chrome DevTools Protocol
- Process Management: psutil
- Security: PBKDF2-HMAC-SHA256 (PIN hashing) + HMAC-signed audit log

**Key Components:**
```
system_focus_manager/
├── main.py                 # Entry point
├── gui.py                  # Main window
├── config_window.py        # Configuration UI
├── process_manager.py      # App control
├── browser_focus/          # Browser CDP control
├── pin_manager.py          # Security
├── stats_manager.py        # Statistics
└── modes/                  # JSON configs
```

---

## 🔒 Security

- **PIN Protection:** PBKDF2-HMAC-SHA256 with a random per-PIN salt
- **Parental Mode:** PIN required to deactivate or change settings
- **Process Control:** Closes unauthorized apps (including Task Manager at the same privilege level) in Ultra Focus
- **Tamper-evident audit log:** HMAC-chained entries detect edits, deletions and reordering

---

## 📊 Statistics

Tracks:
- Total time per mode
- Sessions count
- Apps blocked
- History with timestamps

---

## 🛠️ Building Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico main.py
# Output: dist/main.exe
```

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Commit changes
4. Push and open PR

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

## 🗺️ Roadmap

- [ ] System tray integration
- [ ] Dark theme
- [ ] Export statistics (CSV)
- [ ] Preset configurations
- [ ] Sound notifications
- [ ] Cross-platform support

---

**Made with ⚡ and Python**
