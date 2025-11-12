"""
Driver status endpoint tests.

Covers GET:
- Successful status retrieval (available)
- Successful status retrieval (busy)
- Unauthenticated access rejection
- Manager access rejection (only drivers allowed)

Covers PATCH:
- Successful status update (available -> busy)
- Successful status update (busy -> available)
- Unauthenticated access rejection
- Manager access rejection (only drivers allowed)
- Missing is_active field rejection
- Invalid is_active type rejection
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from shipments.models import Driver, WarehouseManager

User = get_user_model()

DRIVER_STATUS_URL = "/api/v1/driver/status/"


@pytest.mark.api
class TestDriverStatusGet:
    """Test driver status retrieval endpoint (GET)."""

    def test_successful_get_available_status(self, driver_client, driver_user, db):
        """Driver can retrieve their status when available."""
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = True
        driver.save()

        response = driver_client.get(DRIVER_STATUS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is True
        assert response.data["status"] == "متاح"
        assert response.data["id"] == driver_user.id
        assert response.data["username"] == driver_user.username
        assert response.data["phone"] == driver_user.phone

    def test_successful_get_busy_status(self, driver_client, driver_user, db):
        """Driver can retrieve their status when busy."""
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = False
        driver.save()

        response = driver_client.get(DRIVER_STATUS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False
        assert response.data["status"] == "مشغول"

    def test_get_unauthenticated_access_rejected(self, api_client, db):
        """Unauthenticated users cannot retrieve driver status."""
        response = api_client.get(DRIVER_STATUS_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_manager_access_rejected(self, manager_client, manager_user, db):
        """Warehouse managers cannot retrieve driver status (only drivers allowed)."""
        response = manager_client.get(DRIVER_STATUS_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestDriverStatusUpdate:
    """Test driver status update endpoint (PATCH)."""

    def test_successful_update_to_busy(self, driver_client, driver_user, db):
        """Driver can update status from available (True) to busy (False)."""
        # Verify initial state is active (available)
        driver = Driver.objects.get(user=driver_user)
        assert driver.is_active is True

        # Update to busy
        payload = {"is_active": False}
        response = driver_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False
        assert response.data["status"] == "مشغول"
        assert response.data["id"] == driver_user.id
        assert response.data["username"] == driver_user.username
        assert response.data["phone"] == driver_user.phone

        # Verify database was updated
        driver.refresh_from_db()
        assert driver.is_active is False

    def test_successful_update_to_available(self, driver_client, driver_user, db):
        """Driver can update status from busy (False) to available (True)."""
        # Set initial state to busy
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = False
        driver.save()

        # Update to available
        payload = {"is_active": True}
        response = driver_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is True
        assert response.data["status"] == "متاح"

        # Verify database was updated
        driver.refresh_from_db()
        assert driver.is_active is True

    def test_unauthenticated_access_rejected(self, api_client, db):
        """Unauthenticated users cannot update driver status."""
        payload = {"is_active": False}
        response = api_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_manager_access_rejected(self, manager_client, manager_user, db):
        """Warehouse managers cannot update driver status (only drivers allowed)."""
        payload = {"is_active": False}
        response = manager_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_is_active_field(self, driver_client, driver_user, db):
        """Request without is_active field is rejected."""
        response = driver_client.patch(DRIVER_STATUS_URL, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "is_active field is required" in response.data["detail"]

    def test_invalid_is_active_type_string(self, driver_client, driver_user, db):
        """Request with string value for is_active is rejected."""
        payload = {"is_active": "true"}
        response = driver_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "boolean value" in response.data["detail"].lower()

    def test_invalid_is_active_type_number(self, driver_client, driver_user, db):
        """Request with numeric value for is_active is rejected."""
        payload = {"is_active": 1}
        response = driver_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "boolean value" in response.data["detail"].lower()

    def test_invalid_is_active_type_null(self, driver_client, driver_user, db):
        """Request with null value for is_active is rejected."""
        payload = {"is_active": None}
        response = driver_client.patch(DRIVER_STATUS_URL, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

