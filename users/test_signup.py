"""
Signup endpoint tests.

Covers:
- Successful signup creates user and driver profile
- Saudi phone validation (+966...)
- Password confirmation mismatch
- Duplicate phone rejection
"""

import pytest
from django.contrib.auth import get_user_model
from shipments.models import Driver

User = get_user_model()

# URLs without trailing slash to match Django routing
SIGNUP_URL = "/api/v1/auth/signup/"
LOGIN_URL = "/api/v1/auth/login/"


@pytest.mark.api
class TestSignup:
    def test_successful_signup_creates_driver_and_returns_tokens(self, api_client, db):
        """User can sign up with +966 phone; returns JWT and creates Driver profile."""
        payload = {
            "name": "New Driver",
            "phone": "+966512345678",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
        }
        res = api_client.post(SIGNUP_URL, payload, format="json")
        assert res.status_code == 201
        assert "access" in res.data and "refresh" in res.data
        assert res.data["role"] == "driver"

        # phone stored normalized (digits only)
        created = User.objects.get(username="New Driver")
        assert created.phone.isdigit()
        # driver profile created
        assert Driver.objects.filter(user=created).exists()

        # Can login using the same phone in any format (with punctuation removed in view)
        res_login = api_client.post(LOGIN_URL, {"phone": "+966 5 123 45678", "password": "StrongPass123"}, format="json")
        assert res_login.status_code == 200
        assert res_login.data["role"] == "driver"

    def test_reject_invalid_saudi_phone(self, api_client, db):
        """Reject phone not starting with +966 (or wrong length)."""
        bad_payloads = [
            {"name": "A", "phone": "0512345678", "password": "StrongPass123", "password_confirm": "StrongPass123"},
            {"name": "A", "phone": "+967512345678", "password": "StrongPass123", "password_confirm": "StrongPass123"},
            {"name": "A", "phone": "+96651234567", "password": "StrongPass123", "password_confirm": "StrongPass123"},
        ]
        for p in bad_payloads:
            res = api_client.post(SIGNUP_URL, p, format="json")
            assert res.status_code == 400
            assert "phone" in res.data

    def test_password_mismatch(self, api_client, db):
        """Reject when password and password_confirm do not match."""
        payload = {
            "name": "X",
            "phone": "+966512345679",
            "password": "StrongPass123",
            "password_confirm": "StrongPass12X",
        }
        res = api_client.post(SIGNUP_URL, payload, format="json")
        assert res.status_code == 400
        assert "password_confirm" in res.data

    def test_duplicate_phone_rejected(self, api_client, create_user, db):
        """Reject duplicate phone (normalized)."""
        # create existing user with normalized digits
        existing = create_user(username="dup", phone="966512345680")  # digits only
        # try to signup with +966 format for same number
        payload = {
            "name": "Dup2",
            "phone": "+966512345680",
            "password": "StrongPass123",
            "password_confirm": "StrongPass123",
        }
        res = api_client.post(SIGNUP_URL, payload, format="json")
        assert res.status_code == 400
        assert "phone" in res.data


