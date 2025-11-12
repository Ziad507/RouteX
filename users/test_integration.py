"""
Integration tests for user authentication flow.

Tests complete workflows:
- Signup -> Login -> WhoAmI
- Login -> Token Refresh -> WhoAmI
- Signup -> Driver Status Update
"""

import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from shipments.models import Driver

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication workflow."""
    
    SIGNUP_URL = "/api/v1/auth/signup/"
    LOGIN_URL = "/api/v1/auth/login/"
    WHOIS_URL = "/api/v1/auth/whoami/"
    
    def test_signup_login_whois_flow(self, api_client):
        """Test complete flow: signup -> login -> whois."""
        # 1. Signup
        signup_data = {
            "name": "Ahmed Ali",
            "phone": "+966501234567",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!"
        }
        signup_response = api_client.post(self.SIGNUP_URL, signup_data)
        assert signup_response.status_code == status.HTTP_201_CREATED
        assert "access" in signup_response.data
        assert "refresh" in signup_response.data
        assert signup_response.data["role"] == "driver"
        
        # Verify user was created
        user = User.objects.get(phone="966501234567")
        assert user.username == "Ahmed Ali"
        assert Driver.objects.filter(user=user).exists()
        
        # 2. Login with new credentials
        login_data = {
            "phone": "966501234567",
            "password": "SecurePass123!"
        }
        login_response = api_client.post(self.LOGIN_URL, login_data)
        assert login_response.status_code == status.HTTP_200_OK
        assert "access" in login_response.data
        assert "refresh" in login_response.data
        
        # 3. Use access token to get user info
        access_token = login_response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        whois_response = api_client.get(self.WHOIS_URL)
        assert whois_response.status_code == status.HTTP_200_OK
        assert whois_response.data["id"] == user.id
        assert whois_response.data["role"] == "driver"
        assert "phone" in whois_response.data
        # Phone should be masked
        assert whois_response.data["phone"] != "966501234567"
        assert "****" in whois_response.data["phone"]
    
    def test_token_refresh_flow(self, api_client, driver_user):
        """Test token refresh workflow."""
        # 1. Login to get tokens
        login_data = {
            "phone": driver_user.phone,
            "password": "testpass123"
        }
        login_response = api_client.post(self.LOGIN_URL, login_data)
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.data["refresh"]
        
        # 2. Refresh token
        refresh_response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        assert "access" in refresh_response.data
        
        # 3. Use new access token
        new_access_token = refresh_response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access_token}")
        whois_response = api_client.get(self.WHOIS_URL)
        assert whois_response.status_code == status.HTTP_200_OK
        assert whois_response.data["id"] == driver_user.id


@pytest.mark.django_db
@pytest.mark.integration
class TestDriverSignupWorkflow:
    """Test driver signup and status update workflow."""
    
    SIGNUP_URL = "/api/v1/auth/signup/"
    DRIVER_STATUS_URL = "/api/v1/driver/status/"
    
    def test_signup_driver_status_update_flow(self, api_client):
        """Test signup -> check status -> update status."""
        # 1. Signup as driver
        signup_data = {
            "name": "Mohammed Driver",
            "phone": "+966507654321",
            "password": "DriverPass123!",
            "password_confirm": "DriverPass123!"
        }
        signup_response = api_client.post(self.SIGNUP_URL, signup_data)
        assert signup_response.status_code == status.HTTP_201_CREATED
        
        # 2. Authenticate with access token
        access_token = signup_response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        
        # 3. Check initial status (should be available by default)
        status_response = api_client.get(self.DRIVER_STATUS_URL)
        assert status_response.status_code == status.HTTP_200_OK
        assert status_response.data["is_active"] is True
        assert status_response.data["status"] == "متاح"
        
        # 4. Update status to busy
        update_response = api_client.patch(
            self.DRIVER_STATUS_URL,
            {"is_active": False}
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["is_active"] is False
        assert update_response.data["status"] == "مشغول"
        
        # 5. Verify status change persisted
        status_response = api_client.get(self.DRIVER_STATUS_URL)
        assert status_response.status_code == status.HTTP_200_OK
        assert status_response.data["is_active"] is False
        assert status_response.data["status"] == "مشغول"
    
    def test_signup_duplicate_phone_fails(self, api_client):
        """Test that signup with duplicate phone fails."""
        # First signup
        signup_data = {
            "name": "First User",
            "phone": "+966501111111",
            "password": "Pass123!",
            "password_confirm": "Pass123!"
        }
        response1 = api_client.post(self.SIGNUP_URL, signup_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Second signup with same phone (different format)
        signup_data2 = {
            "name": "Second User",
            "phone": "966501111111",  # Same phone, different format
            "password": "Pass456!",
            "password_confirm": "Pass456!"
        }
        response2 = api_client.post(self.SIGNUP_URL, signup_data2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in response2.data or "detail" in response2.data

