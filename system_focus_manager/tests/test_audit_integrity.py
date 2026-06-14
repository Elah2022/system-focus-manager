"""
Tests for the tamper-evident audit log (stats_manager.py).

The audit log is the core of the supervision model: if a monitored user
force-closes the program, it is recorded. These tests prove that the HMAC
chain actually detects tampering (edits / deletions) and that the log can be
exported.

Every test uses a throwaway database in a temp folder, so the real stats.db
is never touched.
"""

import json
import sqlite3
import pytest
from stats_manager import StatsManager


@pytest.fixture
def stats(tmp_path):
    db = tmp_path / "stats.db"
    return StatsManager(db_path=str(db))


def _seed(stats):
    """Record a realistic little session and return its audit row ids."""
    sid = stats.start_session("Ultra Focus")
    stats.log_mode_activation("Ultra Focus", sid)
    stats.log_application_closure_with_active_mode("End Task", "Ultra Focus", sid)
    stats.log_mode_deactivation("Ultra Focus", sid, 25)
    return sid


def _audit_ids(db_path):
    conn = sqlite3.connect(db_path)
    ids = [r[0] for r in conn.execute("SELECT id FROM audit_log ORDER BY id").fetchall()]
    conn.close()
    return ids


def test_clean_log_is_intact(stats):
    _seed(stats)
    result = stats.verify_audit_integrity()
    assert result['intact'] is True
    assert result['checked'] >= 3


def test_editing_a_row_is_detected(stats):
    _seed(stats)
    first_id = _audit_ids(stats.db_path)[0]

    conn = sqlite3.connect(stats.db_path)
    conn.execute("UPDATE audit_log SET event_description=? WHERE id=?", ("FORGED", first_id))
    conn.commit()
    conn.close()

    result = stats.verify_audit_integrity()
    assert result['intact'] is False
    assert "modified" in result['reason'].lower()


def test_deleting_a_row_is_detected(stats):
    _seed(stats)
    ids = _audit_ids(stats.db_path)
    middle_id = ids[len(ids) // 2]  # delete a middle entry -> breaks the chain

    conn = sqlite3.connect(stats.db_path)
    conn.execute("DELETE FROM audit_log WHERE id=?", (middle_id,))
    conn.commit()
    conn.close()

    result = stats.verify_audit_integrity()
    assert result['intact'] is False


def test_export_creates_signed_report(stats, tmp_path):
    _seed(stats)
    out = tmp_path / "audit_export.json"

    assert stats.export_audit_log(str(out)) is True
    assert out.exists()

    data = json.loads(out.read_text(encoding='utf-8'))
    assert 'integrity' in data
    assert 'entries' in data
    assert data['integrity']['intact'] is True
    assert len(data['entries']) >= 3
