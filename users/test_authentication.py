"""
Authentication and authorization tests.

Covers:
- User login with JWT tokens
- Role detection (manager vs driver)
- Permission enforcement
- Error handling
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from shipments.models import Driver, WarehouseManager

User = get_user_model()


@pytest.mark.api
class TestLoginView:
    """Test user login endpoint."""
    
    url = "/api/v1/auth/login/"
    
    def test_successful_manager_login(self, api_client, manager_user):
        """Test successful login as warehouse manager."""
        data = {
            "phone": "0501111111",
            "password": "testpass123"
        }
        response = api_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["role"] == "manager"
        assert response.data["user"]["username"] == "manager"
    
    def test_successful_driver_login(self, api_client, driver_user):
        """Test successful login as driver."""
        data = {
            "phone": "0502222222",
            "password": "testpass123"
        }
        response = api_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "driver"
    
    def test_login_missing_credentials(self, api_client):
        """Test login without phone or password."""
        response = api_client.post(self.url, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        response = api_client.post(self.url, {"phone": "0500000000"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_login_invalid_credentials(self, api_client, manager_user):
        """Test login with wrong password."""
        data = {
            "phone": "0501111111",
            "password": "wrongpassword"
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent phone."""
        data = {
            "phone": "0509999999",
            "password": "testpass123"
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_inactive_user(self, api_client, create_user):
        """Test login with deactivated account."""
        user = create_user(username="inactive", phone="0508888888", is_active=False)
        WarehouseManager.objects.create(user=user)
        
        data = {
            "phone": "0508888888",
            "password": "testpass123"
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_login_user_without_role(self, api_client, create_user):
        """Test login with user that has no role assigned."""
        create_user(username="norole", phone="0507777777")
        
        data = {
            "phone": "0507777777",
            "password": "testpass123"
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "not assigned to any role" in response.data["detail"].lower()
    
    def test_phone_normalization(self, api_client, manager_user):
        """Test that phone number is normalized (spaces, dashes removed)."""
        data = {
            "phone": "050-111-1111",  # With dashes
            "password": "testpass123"
        }
        response = api_client.post(self.url, data)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.api
class TestWhoAmIView:
    """Test user profile retrieval endpoint."""
    
    url = "/api/v1/auth/whoami/"
    
    def test_authenticated_manager(self, manager_client, manager_user):
        """Test profile retrieval for manager."""
        response = manager_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "manager"
        assert response.data["username"] == "manager"
    
    def test_authenticated_driver(self, driver_client, driver_user):
        """Test profile retrieval for driver."""
        response = driver_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "driver"
    
    def test_unauthenticated_access(self, api_client):
        """Test that unauthenticated users cannot access profile."""
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
class TestTokenRefresh:
    """Test JWT token refresh endpoint."""
    
    login_url = "/api/v1/auth/login/"
    refresh_url = "/api/v1/auth/refresh/"
    
    def test_refresh_token(self, api_client, manager_user):
        """Test refreshing access token with valid refresh token."""
        # First login to get tokens
        login_data = {
            "phone": "0501111111",
            "password": "testpass123"
        }
        login_response = api_client.post(self.login_url, login_data)
        refresh_token = login_response.data["refresh"]
        
        # Refresh the access token
        refresh_data = {"refresh": refresh_token}
        refresh_response = api_client.post(self.refresh_url, refresh_data)
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert "access" in refresh_response.data
    
    def test_invalid_refresh_token(self, api_client):
        """Test refresh with invalid token."""
        data = {"refresh": "invalid_token_12345"}
        response = api_client.post(self.refresh_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

