"""
Tests for the process control logic (process_manager.py).

ProcessManager is the most dangerous part of the app because it terminates
processes. These tests verify the *safety rules* WITHOUT killing any real
application:

- Critical Windows processes are on the protected list.
- Asking to close a protected process is refused (returns False, no kill).
- Asking to close a non-existent process is a no-op.
- Read-only helpers (is_process_running / get_process_count) work.

We only ever reference a guaranteed-nonexistent name or the current Python
process, so nothing important is ever closed.
"""

import os
import psutil
import pytest
from process_manager import ProcessManager

# A name that is guaranteed not to be a real running program
FAKE = "definitely_not_a_real_app_xyz123.exe"


@pytest.fixture
def pm():
    return ProcessManager()


def test_critical_processes_are_protected(pm):
    protected = [p.lower() for p in pm.PROTECTED_PROCESSES]
    for name in ['explorer.exe', 'csrss.exe', 'winlogon.exe', 'lsass.exe', 'services.exe']:
        assert name in protected, f"{name} should be protected"


def test_closing_a_protected_process_is_refused(pm):
    # Returns False immediately, without attempting to terminate anything
    assert pm.close_process('explorer.exe') is False
    assert pm.close_process('csrss.exe') is False


def test_closing_a_nonexistent_process_returns_false(pm):
    assert pm.close_process(FAKE) is False


def test_is_process_running_detects_current_process(pm):
    current = psutil.Process(os.getpid()).name()
    assert pm.is_process_running(current) is True


def test_is_process_running_false_for_fake(pm):
    assert pm.is_process_running(FAKE) is False


def test_get_process_count(pm):
    current = psutil.Process(os.getpid()).name()
    assert pm.get_process_count(current) >= 1
    assert pm.get_process_count(FAKE) == 0
