# users/urls.py
"""
Users app URL configuration.

Handles authentication and user profile endpoints.
API versioning: v1
"""

from django.urls import path
from .views import LoginView, whois, SignupView, DriverStatusUpdateView, TokenRefreshView

# API version prefix
API_PREFIX = "api/v1"

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION ENDPOINTS (Public)
    # ============================================================================
    path(f"{API_PREFIX}/auth/signup/", SignupView.as_view(), name="auth-signup"),
    path(f"{API_PREFIX}/auth/login/", LoginView.as_view(), name="auth-login"),
    path(f"{API_PREFIX}/auth/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    
    # ============================================================================
    # USER PROFILE ENDPOINTS (Authenticated)
    # ============================================================================
    path(f"{API_PREFIX}/auth/whoami/", whois, name="auth-whoami"),
    
    # ============================================================================
    # DRIVER STATUS ENDPOINTS (Driver only)
    # ============================================================================
    path(f"{API_PREFIX}/driver/status/", DriverStatusUpdateView.as_view(), name="driver-status-update"),
]


