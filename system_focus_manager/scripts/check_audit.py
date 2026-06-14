"""
Manual diagnostic tool for the audit log.

This is NOT an automated test (those live in ../tests/). It is a hands-on
script that inspects the REAL database in %LOCALAPPDATA%\\FocusManager and can
create a fake incomplete session to check that abrupt-closure detection works.

Because it writes to the real database, it only runs when you launch it
explicitly:

    python scripts/check_audit.py

It does nothing on import, so it is safe for `pytest` to ignore.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Match the app's timestamp format and silence the 3.12 deprecation warning
sqlite3.register_adapter(datetime, lambda val: val.isoformat(" "))


def main():
    app_data = os.path.expandvars('%LOCALAPPDATA%')
    db_path = Path(app_data) / 'FocusManager' / 'data' / 'stats.db'

    print(f"Database path: {db_path}")
    print(f"Database exists: {db_path.exists()}")

    if not db_path.exists():
        print("\nNo database yet. Run the app at least once first.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check sessions
    cursor.execute('SELECT COUNT(*) FROM sessions')
    print(f"\nTotal sessions: {cursor.fetchone()[0]}")

    cursor.execute('SELECT COUNT(*) FROM sessions WHERE end_time IS NULL')
    print(f"Incomplete sessions (end_time IS NULL): {cursor.fetchone()[0]}")

    # Check audit log
    cursor.execute('SELECT COUNT(*) FROM audit_log')
    audit_count = cursor.fetchone()[0]
    print(f"\nTotal audit log entries: {audit_count}")

    if audit_count > 0:
        cursor.execute(
            'SELECT event_type, event_description, timestamp '
            'FROM audit_log ORDER BY timestamp DESC LIMIT 5'
        )
        print("\nLatest audit entries:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]} at {row[2]}")
    else:
        print("\n[!] Audit log is EMPTY!")
        print("This means log_mode_activation/deactivation are not being called.")

    # Manually create a test incomplete session to exercise detection
    print("\n\n=== Testing Detection ===")
    print("Creating a test incomplete session...")
    cursor.execute('''
        INSERT INTO sessions (mode_name, start_time, end_time, duration_minutes)
        VALUES (?, ?, NULL, NULL)
    ''', ('Test Mode', datetime.now()))
    conn.commit()

    cursor.execute('SELECT id, mode_name, start_time FROM sessions WHERE end_time IS NULL')
    abrupt_sessions = cursor.fetchall()
    print(f"Found {len(abrupt_sessions)} incomplete sessions")

    for session_id, mode_name, start_time in abrupt_sessions:
        print(f"  - Session {session_id}: {mode_name} started at {start_time}")
        cursor.execute(
            'UPDATE sessions SET end_time = ?, duration_minutes = 0 WHERE id = ?',
            (start_time, session_id),
        )
        cursor.execute('''
            INSERT INTO audit_log (event_type, event_description, timestamp, mode_name, session_id, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('ABRUPT_CLOSURE',
              'Session closed abruptly (End Task, restart, or crash detected)',
              start_time, mode_name, session_id, 'suspicious'))
        print("  [ok] Marked as ABRUPT_CLOSURE")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM audit_log WHERE event_type = 'ABRUPT_CLOSURE'")
    print(f"\nTotal ABRUPT_CLOSURE entries: {cursor.fetchone()[0]}")

    conn.close()
    print("\n[ok] Diagnostic complete!")


if __name__ == '__main__':
    main()
