"""
Here I save all my statistics in a SQLite database.
I record how much time I spend in each mode and which apps I close.
"""

import json
import sqlite3
import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Python 3.12 deprecated the implicit datetime->text adapter for sqlite3.
# Register an explicit one that reproduces the previous default format
# ("YYYY-MM-DD HH:MM:SS.ffffff"). This keeps stored timestamps — and the audit
# hash chain that depends on str(timestamp) — byte-for-byte identical, while
# silencing the deprecation warning.
sqlite3.register_adapter(datetime, lambda val: val.isoformat(" "))


class StatsManager:
    """My statistics manager that uses SQLite to save everything"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use LOCALAPPDATA for persistent storage (works in both dev and .exe)
            app_data = os.path.expandvars('%LOCALAPPDATA%')
            db_path = Path(app_data) / 'FocusManager' / 'data' / 'stats.db'

        # Create directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._audit_key = self._load_or_create_audit_key()
        self._init_database()

    def _load_or_create_audit_key(self) -> bytes:
        """
        Load (or create) the secret key used to sign audit-log entries.

        NOTE: the key is stored locally next to the data. This raises the bar
        against CASUAL tampering — deleting, editing or reordering rows becomes
        detectable via verify_audit_integrity() — but a determined user with
        the key could still re-sign a forged log. The real fix is to push the
        log off the machine (see export_audit_log()).
        """
        try:
            key_path = Path(self.db_path).parent.parent / 'config' / 'audit.key'
            key_path.parent.mkdir(parents=True, exist_ok=True)
            if key_path.exists():
                return key_path.read_bytes()
            key = secrets.token_bytes(32)
            key_path.write_bytes(key)
            return key
        except Exception:
            # Fallback: deterministic key so the app keeps working (weaker)
            return hashlib.sha256(b'focus-manager-audit-fallback-key').digest()

    def _compute_entry_hash(self, prev_hash, event_type, description,
                            timestamp, mode_name, session_id, severity) -> str:
        """Compute the HMAC of an audit entry, chained to the previous one."""
        payload = '|'.join([
            str(prev_hash),
            str(event_type),
            str(description),
            str(timestamp),
            str(mode_name),
            str(session_id),
            str(severity),
        ])
        return hmac.new(self._audit_key, payload.encode('utf-8'), hashlib.sha256).hexdigest()

    def _get_last_entry_hash(self, cursor) -> str:
        """Return the hash of the most recent audit entry (genesis if none)."""
        cursor.execute('SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        return '0' * 64  # genesis

    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode_name TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_minutes INTEGER,
                apps_closed INTEGER DEFAULT 0,
                apps_opened INTEGER DEFAULT 0
            )
        ''')

        # Closed apps table (for statistics)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS closed_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                closed_at TIMESTAMP NOT NULL,
                mode_name TEXT NOT NULL
            )
        ''')

        # Audit log table (for detecting cheating/abrupt closures)
        # prev_hash / entry_hash form a tamper-evident HMAC chain.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_description TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                mode_name TEXT,
                session_id INTEGER,
                severity TEXT DEFAULT 'normal',
                prev_hash TEXT,
                entry_hash TEXT
            )
        ''')

        # Migrate older databases that lack the tamper-evidence columns
        for col in ('prev_hash', 'entry_hash'):
            try:
                cursor.execute(f'ALTER TABLE audit_log ADD COLUMN {col} TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists

        conn.commit()
        conn.close()

        # Check for abrupt closures on initialization
        self._detect_abrupt_closures()

    def start_session(self, mode_name: str) -> int:
        """
        Start a new session.
        Returns the session ID.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO sessions (mode_name, start_time)
            VALUES (?, ?)
        ''', (mode_name, datetime.now()))

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return session_id

    def end_session(self, session_id: int):
        """End a session and calculate duration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get start time
        cursor.execute('SELECT start_time FROM sessions WHERE id = ?', (session_id,))
        result = cursor.fetchone()

        if result:
            start_time = datetime.fromisoformat(result[0])
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() / 60)  # minutes

            cursor.execute('''
                UPDATE sessions
                SET end_time = ?, duration_minutes = ?
                WHERE id = ?
            ''', (end_time, duration, session_id))

        conn.commit()
        conn.close()

    def record_closed_app(self, app_name: str, mode_name: str):
        """Record that an app was closed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO closed_apps (app_name, closed_at, mode_name)
            VALUES (?, ?, ?)
        ''', (app_name, datetime.now(), mode_name))

        conn.commit()
        conn.close()

    def update_session_counts(self, session_id: int, apps_closed: int, apps_opened: int):
        """Update app counters in the session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE sessions
            SET apps_closed = ?, apps_opened = ?
            WHERE id = ?
        ''', (apps_closed, apps_opened, session_id))

        conn.commit()
        conn.close()

    def get_stats_this_week(self) -> Dict:
        """Get statistics for the current week"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Week start date
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())

        # Total sessions
        cursor.execute('''
            SELECT COUNT(*) FROM sessions
            WHERE start_time >= ?
        ''', (week_start,))
        total_sessions = cursor.fetchone()[0]

        # Time per mode
        cursor.execute('''
            SELECT mode_name, SUM(duration_minutes), COUNT(*)
            FROM sessions
            WHERE start_time >= ? AND duration_minutes IS NOT NULL
            GROUP BY mode_name
        ''', (week_start,))

        modes_data = {}
        total_minutes = 0

        for row in cursor.fetchall():
            mode_name, minutes, count = row
            hours = round(minutes / 60, 1)
            modes_data[mode_name] = {
                'sessions': count,
                'minutes': minutes,
                'hours': hours
            }
            total_minutes += minutes

        # Most closed apps
        cursor.execute('''
            SELECT app_name, COUNT(*) as count
            FROM closed_apps
            WHERE closed_at >= ?
            GROUP BY app_name
            ORDER BY count DESC
        ''', (week_start,))

        most_closed = [{'app': row[0], 'count': row[1]} for row in cursor.fetchall()]

        conn.close()

        return {
            'total_sessions': total_sessions,
            'total_hours': round(total_minutes / 60, 1),
            'modes': modes_data,
            'most_closed_apps': most_closed
        }

    def get_stats_today(self) -> Dict:
        """Get statistics for the current day"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        cursor.execute('''
            SELECT mode_name, SUM(duration_minutes), COUNT(*)
            FROM sessions
            WHERE start_time >= ? AND duration_minutes IS NOT NULL
            GROUP BY mode_name
        ''', (today_start,))

        modes_data = {}
        for row in cursor.fetchall():
            mode_name, minutes, count = row
            modes_data[mode_name] = {
                'sessions': count,
                'minutes': minutes,
                'hours': round(minutes / 60, 1)
            }

        conn.close()
        return modes_data

    def export_to_json(self, filepath: str):
        """Export statistics to JSON"""
        stats = self.get_stats_this_week()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

    # ===== AUDIT LOG METHODS =====

    def _detect_abrupt_closures(self):
        """
        Detect sessions that were not closed properly (End Task, crash, power off, etc.)
        Called on program startup to check for incomplete sessions.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find sessions without end_time
        cursor.execute('''
            SELECT id, mode_name, start_time
            FROM sessions
            WHERE end_time IS NULL
        ''')

        abrupt_sessions = cursor.fetchall()

        for session_id, mode_name, start_time in abrupt_sessions:
            # Detect the type of closure
            closure_type, closure_description = self._detect_closure_type(start_time)

            # Mark session as abruptly closed
            cursor.execute('''
                UPDATE sessions
                SET end_time = ?, duration_minutes = 0
                WHERE id = ?
            ''', (start_time, session_id))

            # Log the abrupt closure with specific details
            self._log_audit_event(
                event_type='ABRUPT_CLOSURE',
                description=closure_description,
                mode_name=mode_name,
                session_id=session_id,
                severity='suspicious',
                timestamp=start_time,
                cursor=cursor
            )

        conn.commit()
        conn.close()

    def _detect_closure_type(self, start_time):
        """
        Detect what caused the abrupt closure.
        Returns (type, description) tuple.

        NOTE: This is a best-effort heuristic. We CANNOT know with 100% certainty
        how the program was closed since Windows doesn't tell us.

        We can ONLY be certain about:
        - System restart/shutdown (by checking boot time)

        Everything else (End Task, crash, kill process) looks the same to us.
        """
        try:
            import psutil
            from datetime import datetime

            # Parse start time
            if isinstance(start_time, str):
                session_start = datetime.fromisoformat(start_time)
            else:
                session_start = start_time

            now = datetime.now()
            time_since_session = (now - session_start).total_seconds()

            # Get system boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())

            # ONLY RELIABLE DETECTION: Check if system was rebooted/shutdown
            if boot_time > session_start:
                # System was definitely rebooted or shut down
                time_between = (boot_time - session_start).total_seconds()
                minutes_between = int(time_between / 60)
                hours_between = int(time_between / 3600)

                if hours_between > 0:
                    return ('SHUTDOWN_OR_RESTART', f'💤 System shut down/restarted ({hours_between}h after session started)')
                elif minutes_between > 1:
                    return ('SHUTDOWN_OR_RESTART', f'💤 System shut down/restarted ({minutes_between} min after session)')
                else:
                    return ('SHUTDOWN_OR_RESTART', f'💤 System shut down/restarted ({int(time_between)}s after session)')

            # If no reboot detected, we CANNOT be sure if it was:
            # - End Task from Task Manager
            # - Application crash
            # - Kill process command
            # - Power loss
            # They all look identical to us!

            # So we just report "abrupt closure" with timing info
            hours_ago = int(time_since_session / 3600)
            minutes_ago = int(time_since_session / 60)

            if hours_ago > 24:
                days_ago = int(hours_ago / 24)
                return ('ABRUPT', f'Closed unexpectedly {days_ago}d ago (End Task, crash, or power loss)')
            elif hours_ago > 0:
                return ('ABRUPT', f'Closed unexpectedly {hours_ago}h ago (End Task, crash, or power loss)')
            elif minutes_ago > 5:
                return ('ABRUPT', f'Closed unexpectedly {minutes_ago} min ago (End Task, crash, or power loss)')
            else:
                return ('ABRUPT', f'Closed unexpectedly {int(time_since_session)}s ago (End Task, crash, or power loss)')

        except Exception as e:
            # Fallback
            return ('UNKNOWN', f'Closed unexpectedly (details unavailable)')


    def _log_audit_event(self, event_type: str, description: str,
                         mode_name: str = None, session_id: int = None,
                         severity: str = 'normal', timestamp: datetime = None,
                         cursor=None):
        """
        Log an audit event.
        severity can be: 'normal', 'warning', 'suspicious', 'critical'
        """
        should_close = False
        if cursor is None:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            should_close = True

        if timestamp is None:
            timestamp = datetime.now()

        # Sign this entry, chained to the previous one (tamper-evidence)
        prev_hash = self._get_last_entry_hash(cursor)
        entry_hash = self._compute_entry_hash(
            prev_hash, event_type, description, str(timestamp),
            mode_name, session_id, severity
        )

        cursor.execute('''
            INSERT INTO audit_log (event_type, event_description, timestamp, mode_name, session_id, severity, prev_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_type, description, timestamp, mode_name, session_id, severity, prev_hash, entry_hash))

        if should_close:
            conn.commit()
            conn.close()

    def log_mode_activation(self, mode_name: str, session_id: int):
        """Log when a mode is activated"""
        self._log_audit_event(
            event_type='MODE_ACTIVATED',
            description=f'Mode "{mode_name}" activated',
            mode_name=mode_name,
            session_id=session_id,
            severity='normal'
        )

    def log_mode_deactivation(self, mode_name: str, session_id: int, duration_minutes: int):
        """Log when a mode is deactivated normally"""
        self._log_audit_event(
            event_type='MODE_DEACTIVATED',
            description=f'Mode "{mode_name}" deactivated normally (Duration: {duration_minutes} min)',
            mode_name=mode_name,
            session_id=session_id,
            severity='normal'
        )

    def log_application_closure(self, closure_method: str):
        """Log when the application is closed normally (no active mode)"""
        self._log_audit_event(
            event_type='APP_CLOSED',
            description=f'Application closed normally ({closure_method})',
            mode_name=None,
            session_id=None,
            severity='normal'
        )

    def log_application_closure_with_active_mode(self, closure_method: str, mode_name: str, session_id: int):
        """Log when the application is closed WITH an active mode (user didn't deactivate first)"""
        self._log_audit_event(
            event_type='APP_CLOSED',
            description=f'Application closed without deactivating mode "{mode_name}" first ({closure_method})',
            mode_name=mode_name,
            session_id=session_id,
            severity='normal'
        )

    def get_audit_log(self, days: int = 7) -> List[Dict]:
        """
        Get audit log entries from the last N days.
        Returns a list of dictionaries with audit information.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute('''
            SELECT event_type, event_description, timestamp, mode_name, session_id, severity
            FROM audit_log
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', (cutoff_date,))

        entries = []
        for row in cursor.fetchall():
            entries.append({
                'event_type': row[0],
                'description': row[1],
                'timestamp': row[2],
                'mode_name': row[3],
                'session_id': row[4],
                'severity': row[5]
            })

        conn.close()
        return entries

    def delete_audit_event(self, timestamp: str):
        """Delete a specific audit log event by timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM audit_log
            WHERE timestamp = ?
        ''', (timestamp,))

        conn.commit()
        conn.close()

    def clear_all_audit_log(self):
        """Clear all audit log entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM audit_log')

        conn.commit()
        conn.close()

    def verify_audit_integrity(self) -> Dict:
        """
        Verify the audit-log HMAC chain.

        Detects entries that were edited, deleted, or reordered after being
        recorded. Entries created before tamper-evidence existed (no hash) are
        skipped, so upgrading an old database does not raise a false alarm.

        Returns a dict:
            {'intact': bool, 'total': int, 'checked': int,
             'first_broken_id': Optional[int], 'reason': str}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, event_type, event_description, timestamp,
                   mode_name, session_id, severity, prev_hash, entry_hash
            FROM audit_log ORDER BY id ASC
        ''')
        rows = cursor.fetchall()
        conn.close()

        prev = '0' * 64  # genesis
        checked = 0
        for row in rows:
            (rid, event_type, description, timestamp,
             mode_name, session_id, severity, stored_prev, stored_entry) = row

            # Legacy row created before tamper-evidence: skip, keep chain anchor
            if not stored_entry:
                continue

            if stored_prev != prev:
                return {
                    'intact': False, 'total': len(rows), 'checked': checked,
                    'first_broken_id': rid,
                    'reason': 'Chain broken: an earlier entry was deleted or reordered',
                }

            expected = self._compute_entry_hash(
                prev, event_type, description, str(timestamp),
                mode_name, session_id, severity
            )
            if not hmac.compare_digest(expected, stored_entry):
                return {
                    'intact': False, 'total': len(rows), 'checked': checked,
                    'first_broken_id': rid,
                    'reason': 'An entry was modified after being recorded',
                }

            prev = stored_entry
            checked += 1

        return {
            'intact': True, 'total': len(rows), 'checked': checked,
            'first_broken_id': None, 'reason': 'OK',
        }

    def export_audit_log(self, export_path: str, days: int = 365) -> bool:
        """
        Export the audit log (plus an integrity verdict) to a JSON file.

        Saving this file somewhere the monitored user cannot reach — a teacher's
        email, a shared drive, a USB stick — is what truly protects the evidence:
        even if stats.db is wiped locally, the supervisor keeps a signed copy.
        """
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'integrity': self.verify_audit_integrity(),
                'entries': self.get_audit_log(days=days),
            }
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception:
            return False
