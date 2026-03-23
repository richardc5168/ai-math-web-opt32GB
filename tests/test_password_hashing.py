"""R35/EXP-P4-01: Password hashing upgrade tests.

Validates:
  1. _pwd_hash produces bcrypt hashes (starts with $2b$)
  2. _pwd_ok verifies bcrypt hashes correctly
  3. _pwd_ok still verifies legacy SHA-256 hashes (backward compat)
  4. Legacy SHA-256 timing-safe comparison via hmac.compare_digest
  5. Admin token comparison uses hmac.compare_digest (timing-safe)
  6. bcrypt hashes are unique even for same password (random salt)
"""
import hashlib
import hmac
import importlib
import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Helpers: import server password functions without starting the app
# ---------------------------------------------------------------------------

def _get_server_module():
    """Return the server module — import only the helpers we need."""
    # server.py is importable as a module; we need _pwd_hash, _pwd_ok,
    # _legacy_sha256_hash
    import server
    return server


@pytest.fixture(scope="module")
def srv():
    return _get_server_module()


# ---------------------------------------------------------------------------
# 1. _pwd_hash produces bcrypt
# ---------------------------------------------------------------------------

class TestPwdHashBcrypt:
    def test_produces_bcrypt_prefix(self, srv):
        h = srv._pwd_hash("mypassword", "ignored-salt")
        assert h.startswith("$2b$"), f"Expected bcrypt hash, got: {h[:20]}"

    def test_hash_is_string(self, srv):
        h = srv._pwd_hash("test123", "")
        assert isinstance(h, str)

    def test_hash_length_is_60(self, srv):
        h = srv._pwd_hash("hello", "")
        assert len(h) == 60, f"bcrypt hash should be 60 chars, got {len(h)}"

    def test_different_calls_produce_different_hashes(self, srv):
        h1 = srv._pwd_hash("samepassword", "")
        h2 = srv._pwd_hash("samepassword", "")
        assert h1 != h2, "bcrypt should produce different hashes each time (random salt)"

    def test_salt_param_ignored(self, srv):
        """The salt parameter is kept for API compat but not used by bcrypt."""
        h1 = srv._pwd_hash("pw", "salt_a")
        h2 = srv._pwd_hash("pw", "salt_b")
        # Both are valid bcrypt, both different (random internal salt)
        assert h1.startswith("$2b$")
        assert h2.startswith("$2b$")


# ---------------------------------------------------------------------------
# 2. _pwd_ok verifies bcrypt hashes
# ---------------------------------------------------------------------------

class TestPwdOkBcrypt:
    def test_correct_password_matches(self, srv):
        h = srv._pwd_hash("correctpassword", "")
        assert srv._pwd_ok("correctpassword", "", h) is True

    def test_wrong_password_fails(self, srv):
        h = srv._pwd_hash("correctpassword", "")
        assert srv._pwd_ok("wrongpassword", "", h) is False

    def test_empty_password(self, srv):
        h = srv._pwd_hash("", "")
        assert srv._pwd_ok("", "", h) is True
        assert srv._pwd_ok("notempty", "", h) is False


# ---------------------------------------------------------------------------
# 3. Legacy SHA-256 backward compat
# ---------------------------------------------------------------------------

class TestLegacySha256Compat:
    def _make_legacy_hash(self, password, salt):
        raw = f"{salt}:{password}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def test_legacy_hash_still_verifies(self, srv):
        salt = "abc123"
        legacy = self._make_legacy_hash("oldpassword", salt)
        assert srv._pwd_ok("oldpassword", salt, legacy) is True

    def test_legacy_wrong_password_fails(self, srv):
        salt = "abc123"
        legacy = self._make_legacy_hash("oldpassword", salt)
        assert srv._pwd_ok("wrongpassword", salt, legacy) is False

    def test_legacy_sha256_hash_function_exists(self, srv):
        h = srv._legacy_sha256_hash("test", "salt")
        expected = hashlib.sha256(b"salt:test").hexdigest()
        assert h == expected

    def test_empty_hash_returns_false(self, srv):
        assert srv._pwd_ok("anything", "salt", "") is False
        assert srv._pwd_ok("anything", "salt", None) is False


# ---------------------------------------------------------------------------
# 4. Admin token uses hmac.compare_digest (source inspection)
# ---------------------------------------------------------------------------

class TestTimingSafeComparison:
    def test_admin_reset_uses_compare_digest(self):
        """Verify that admin_reset_password source contains hmac.compare_digest."""
        import inspect
        import server
        src = inspect.getsource(server.admin_reset_password)
        assert "hmac.compare_digest" in src, "admin_reset_password must use hmac.compare_digest"

    def test_admin_provision_uses_compare_digest(self):
        import inspect
        import server
        src = inspect.getsource(server.app_auth_provision)
        assert "hmac.compare_digest" in src, "app_auth_provision must use hmac.compare_digest"

    def test_admin_login_failures_uses_compare_digest(self):
        import inspect
        import server
        src = inspect.getsource(server.admin_login_failures)
        assert "hmac.compare_digest" in src, "admin_login_failures must use hmac.compare_digest"

    def test_no_raw_equality_in_admin_token_checks(self):
        """Ensure no == comparison for admin tokens."""
        import inspect
        import server
        for fn_name in ["admin_reset_password", "app_auth_provision", "admin_login_failures"]:
            fn = getattr(server, fn_name)
            src = inspect.getsource(fn)
            assert "x_admin_token != expected" not in src, (
                f"{fn_name} must not use x_admin_token != expected"
            )
            assert "x_admin_token == expected" not in src, (
                f"{fn_name} must not use x_admin_token == expected"
            )


# ---------------------------------------------------------------------------
# 5. Password hash does not use SHA-256 for new hashes
# ---------------------------------------------------------------------------

class TestNoSha256ForNewHashes:
    def test_pwd_hash_not_sha256_length(self, srv):
        h = srv._pwd_hash("test", "salt")
        # SHA-256 hex digest is 64 chars, bcrypt is 60
        assert len(h) != 64, "New hashes should not be SHA-256 length"

    def test_pwd_hash_not_all_hex(self, srv):
        h = srv._pwd_hash("test", "salt")
        # SHA-256 produces only hex chars; bcrypt includes $, /, . etc.
        try:
            int(h, 16)
            pytest.fail("Hash should not be pure hex (SHA-256)")
        except ValueError:
            pass  # Expected — bcrypt hashes contain non-hex chars
