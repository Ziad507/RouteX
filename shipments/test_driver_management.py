"""
Driver management tests for manager endpoints.

Covers:
- GET /api/v1/drivers/<id>/ (manager only)
- DELETE /api/v1/drivers/<id>/ (manager only)
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from shipments.models import Driver

User = get_user_model()

DRIVER_LIST_URL = "/api/v1/drivers/"
DRIVER_DETAIL_URL = "/api/v1/drivers/{driver_id}/"


@pytest.mark.api
class TestDriverDetailManager:
    """Tests for manager CRUD on drivers."""

    def test_manager_can_get_driver_detail(self, manager_client, driver_user, db):
        driver = Driver.objects.get(user=driver_user)
        response = manager_client.get(DRIVER_DETAIL_URL.format(driver_id=driver.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == driver.id
        assert response.data["user_id"] == driver_user.id
        assert response.data["username"] == driver_user.username
        assert response.data["phone"] == driver_user.phone
        assert response.data["is_active"] is True
        assert response.data["status"] == "available"

    def test_get_driver_returns_busy_status(self, manager_client, driver_user, db):
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = False
        driver.save()

        response = manager_client.get(DRIVER_DETAIL_URL.format(driver_id=driver.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "busy"

    def test_get_driver_not_found(self, manager_client, db):
        response = manager_client.get(DRIVER_DETAIL_URL.format(driver_id=9999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_driver_requires_manager(self, driver_client, driver_user, db):
        driver = Driver.objects.get(user=driver_user)
        response = driver_client.get(DRIVER_DETAIL_URL.format(driver_id=driver.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_delete_driver(self, manager_client, driver_user, db):
        driver = Driver.objects.get(user=driver_user)
        response = manager_client.delete(DRIVER_DETAIL_URL.format(driver_id=driver.id))

        assert response.status_code == status.HTTP_200_OK
        assert not Driver.objects.filter(id=driver.id).exists()
        assert not User.objects.filter(id=driver_user.id).exists()

    def test_delete_driver_not_found(self, manager_client, db):
        response = manager_client.delete(DRIVER_DETAIL_URL.format(driver_id=9999))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_driver_requires_manager(self, api_client, driver_user, db):
        driver = Driver.objects.get(user=driver_user)
        response = api_client.delete(DRIVER_DETAIL_URL.format(driver_id=driver.id))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestDriverListManager:
    """Verify managers see live driver status updates in the collection response."""

    def test_list_includes_active_flag(self, manager_client, driver_user, db):
        response = manager_client.get(DRIVER_LIST_URL)
        assert response.status_code == status.HTTP_200_OK
        driver_payload = response.data["results"][0]
        assert driver_payload["is_active"] is True
        assert driver_payload["status"] == "Available"

    def test_list_reflects_driver_toggle(self, manager_client, driver_user, db):
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = False
        driver.save(update_fields=["is_active"])

        response = manager_client.get(DRIVER_LIST_URL)
        driver_payload = response.data["results"][0]

        assert driver_payload["is_active"] is False
        assert driver_payload["status"] == "Unavailable"  # is_active=False maps to "Unavailable"


