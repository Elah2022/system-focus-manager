"""
Tests for the PIN security (pin_manager.py).

These verify the most important security guarantees:
- PINs are stored with salted PBKDF2 (not plain SHA-256).
- A correct PIN validates and a wrong one does not.
- Old SHA-256 PINs keep working and are upgraded transparently.
- Security questions work.

None of these tests touch the real PIN config file: a temp file is used.
"""

import hashlib
import pytest
from pin_manager import PINManager


@pytest.fixture
def pin(tmp_path):
    """A PINManager isolated to a temp config file (never touches real config)."""
    mgr = PINManager()
    mgr.config_file = tmp_path / "pin_config.json"
    mgr.config = {
        'pin_enabled': False,
        'pin_hash': None,
        'parental_mode': False,
        'require_pin_to_exit': False,
        'security_question': None,
        'security_answer_hash': None,
    }
    return mgr


def test_hash_pin_uses_pbkdf2(pin):
    h = pin.hash_pin("1234")
    assert h.startswith("pbkdf2_sha256$")
    # Random salt means hashing the same PIN twice gives different results
    assert pin.hash_pin("1234") != h


def test_verify_correct_and_wrong_pin(pin):
    h = pin.hash_pin("1234")
    assert pin._verify_hash("1234", h) is True
    assert pin._verify_hash("0000", h) is False


def test_legacy_sha256_still_verifies(pin):
    legacy = hashlib.sha256("1234".encode()).hexdigest()
    assert pin._verify_hash("1234", legacy) is True
    assert pin._verify_hash("9999", legacy) is False


def test_is_legacy_hash(pin):
    legacy = hashlib.sha256("1234".encode()).hexdigest()
    assert pin._is_legacy_hash(legacy) is True
    assert pin._is_legacy_hash(pin.hash_pin("1234")) is False


def test_set_and_verify_pin(pin):
    assert pin.set_pin("4321") is True
    assert pin.verify_pin("4321") is True
    assert pin.verify_pin("0000") is False


def test_pin_too_short_is_rejected(pin):
    assert pin.set_pin("12") is False


def test_legacy_pin_is_upgraded_on_login(pin):
    # Simulate an old config that still has a plain SHA-256 PIN
    pin.config['pin_enabled'] = True
    pin.config['pin_hash'] = hashlib.sha256("1234".encode()).hexdigest()
    assert pin._is_legacy_hash(pin.config['pin_hash'])

    # A correct login should succeed AND migrate the hash to PBKDF2
    assert pin.verify_pin("1234") is True
    assert pin.config['pin_hash'].startswith("pbkdf2_sha256$")

    # And it must keep working after the upgrade
    assert pin.verify_pin("1234") is True
    assert pin.verify_pin("0000") is False


def test_security_answers(pin):
    pin.set_pin("1234", security_questions=[
        {'question': 'pet?', 'answer': 'Rex'},
        {'question': 'city?', 'answer': 'Cali'},
    ])
    # Answers are case-insensitive and trimmed
    assert pin.verify_security_answers({'pet?': 'rex', 'city?': ' CALI '}) is True
    # One wrong answer fails the "all must match" check
    assert pin.verify_security_answers({'pet?': 'rex', 'city?': 'wrong'}) is False
    # ...but "at least one correct" still passes
    assert pin.verify_any_security_answer({'pet?': 'rex', 'city?': 'wrong'}) is True
