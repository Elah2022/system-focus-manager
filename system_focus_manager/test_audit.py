"""Test script to verify audit log functionality"""
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Get database path
app_data = os.path.expandvars('%LOCALAPPDATA%')
db_path = Path(app_data) / 'FocusManager' / 'data' / 'stats.db'

print(f"Database path: {db_path}")
print(f"Database exists: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check sessions
    cursor.execute('SELECT COUNT(*) FROM sessions')
    session_count = cursor.fetchone()[0]
    print(f"\nTotal sessions: {session_count}")

    cursor.execute('SELECT COUNT(*) FROM sessions WHERE end_time IS NULL')
    incomplete = cursor.fetchone()[0]
    print(f"Incomplete sessions (end_time IS NULL): {incomplete}")

    # Check audit log
    cursor.execute('SELECT COUNT(*) FROM audit_log')
    audit_count = cursor.fetchone()[0]
    print(f"\nTotal audit log entries: {audit_count}")

    if audit_count > 0:
        cursor.execute('SELECT event_type, event_description, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 5')
        print("\nLatest audit entries:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}: {row[1]} at {row[2]}")
    else:
        print("\n⚠️ Audit log is EMPTY!")
        print("This means log_mode_activation/deactivation are not being called.")

    # Manually create a test session without end_time
    print("\n\n=== Testing Detection ===")
    print("Creating a test incomplete session...")
    cursor.execute('''
        INSERT INTO sessions (mode_name, start_time, end_time, duration_minutes)
        VALUES (?, ?, NULL, NULL)
    ''', ('Test Mode', datetime.now()))
    conn.commit()

    print("Session created. Now running detection...")

    # Run detection
    cursor.execute('SELECT id, mode_name, start_time FROM sessions WHERE end_time IS NULL')
    abrupt_sessions = cursor.fetchall()

    print(f"Found {len(abrupt_sessions)} incomplete sessions")

    for session_id, mode_name, start_time in abrupt_sessions:
        print(f"  - Session {session_id}: {mode_name} started at {start_time}")

        # Mark as closed
        cursor.execute('''
            UPDATE sessions
            SET end_time = ?, duration_minutes = 0
            WHERE id = ?
        ''', (start_time, session_id))

        # Log the abrupt closure
        cursor.execute('''
            INSERT INTO audit_log (event_type, event_description, timestamp, mode_name, session_id, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('ABRUPT_CLOSURE',
              f'Session closed abruptly (End Task, restart, or crash detected)',
              start_time, mode_name, session_id, 'suspicious'))

        print(f"  ✅ Marked as ABRUPT_CLOSURE")

    conn.commit()

    # Verify
    cursor.execute('SELECT COUNT(*) FROM audit_log WHERE event_type = "ABRUPT_CLOSURE"')
    abrupt_count = cursor.fetchone()[0]
    print(f"\nTotal ABRUPT_CLOSURE entries: {abrupt_count}")

    conn.close()
    print("\n✅ Test complete!")
