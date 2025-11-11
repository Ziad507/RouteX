# users/views.py
"""
User authentication and profile views.

This module handles:
- User login with JWT token generation
- Role detection (Warehouse Manager vs Driver)
- User profile information retrieval
"""

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from shipments.models import WarehouseManager, Driver
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number by extracting only digits.
    
    Args:
        phone: Raw phone number string
        
    Returns:
        String containing only digits from the input
    """
    return ''.join(ch for ch in (phone or '') if ch.isdigit())


def detect_user_role(user) -> str:
    """
    Detect user role based on profile associations.
    
    Args:
        user: User instance
        
    Returns:
        'manager' or 'driver'
        
    Raises:
        PermissionDenied: If user has no valid role assigned
    """
    if WarehouseManager.objects.filter(user=user).exists():
        return 'manager'
    elif Driver.objects.filter(user=user).exists():
        return 'driver'
    else:
        # User exists but has no role - this is a configuration error
        logger.warning(f"User {user.username} (ID: {user.id}) has no role assigned")
        raise PermissionDenied(
            "Your account is not assigned to any role. "
            "Please contact the administrator."
        )


class LoginView(APIView):
    """
    User login endpoint with JWT token generation.
    
    POST /api/login
    Body: {"phone": "0500000000", "password": "********"}
    Returns: {"access": "...", "refresh": "...", "role": "manager|driver", "user": {...}}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Handle user login with phone and password."""
        phone = request.data.get('phone')
        password = request.data.get('password')

        # Validate required fields
        if not phone or not password:
            return Response(
                {'detail': 'Phone and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Normalize phone number
        phone_norm = normalize_phone(phone)
        
        if not phone_norm:
            return Response(
                {'detail': 'Invalid phone number format.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Authenticate user
        try:
            user = User.objects.get(phone=phone_norm)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Verify password and active status
        if not user.check_password(password):
            return Response(
                {'detail': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        if not user.is_active:
            return Response(
                {'detail': 'Account is deactivated. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Detect user role
        try:
            role = detect_user_role(user)
        except PermissionDenied as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Log successful login
        logger.info(f"Successful login: {user.username} ({role})")

        return Response({
            'access': str(access),
            'refresh': str(refresh),
            'role': role,
            'user': {
                'id': user.id,
                'username': user.username,
                'phone': user.phone,
            }
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def whois(request):
    """
    Return authenticated user information and role.
    
    GET /api/whois
    Headers: Authorization: Bearer <access_token>
    Returns: {"id": 1, "username": "...", "phone": "...", "role": "manager|driver"}
    """
    user = request.user
    
    try:
        role = detect_user_role(user)
    except PermissionDenied as e:
        return Response(
            {'detail': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    
    return Response({
        'id': user.id,
        'username': user.username,
        'phone': user.phone,
        'role': role,
    }, status=status.HTTP_200_OK)

