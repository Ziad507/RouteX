# users/urls.py
"""
Users app URL configuration.

Handles authentication and user profile endpoints.
API versioning: v1
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, whois

# API version prefix
API_PREFIX = "api/v1"

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION ENDPOINTS (Public)
    # ============================================================================
    path(f"{API_PREFIX}/auth/login/", LoginView.as_view(), name="auth-login"),
    path(f"{API_PREFIX}/auth/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    
    # ============================================================================
    # USER PROFILE ENDPOINTS (Authenticated)
    # ============================================================================
    path(f"{API_PREFIX}/auth/whoami/", whois, name="auth-whoami"),
]


