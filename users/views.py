# users/views.py
"""
User authentication and profile views.

This module handles:
- User login with JWT token generation
- Role detection (Warehouse Manager vs Driver)
- User profile information retrieval
"""

from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import serializers
from shipments.models import WarehouseManager, Driver
from shipments.permissions import IsDriver
from django.db import transaction, IntegrityError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiTypes, inline_serializer
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(
    tags=["Auth"],
    summary="تحديث Access Token",
    description="يستخدم Refresh Token للحصول على Access Token جديد.",
)
class TokenRefreshView(BaseTokenRefreshView):
    """Wrapper for TokenRefreshView with Swagger documentation."""
    pass


from .utils import normalize_phone, mask_phone


def detect_user_role(user: get_user_model()) -> str:
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

    @extend_schema(
        tags=["Auth"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "example": "+966512345678"},
                    "password": {"type": "string", "example": "StrongPass123"},
                },
                "required": ["phone", "password"],
            }
        },
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Successful login",
                examples=[
                    OpenApiExample(
                        "LoginSuccess",
                        value={
                            "access": "jwt-access-token",
                            "refresh": "jwt-refresh-token",
                            "role": "driver",
                            "user": {"id": 1, "username": "Ahmed", "phone": "966512345678"},
                        },
                    )
                ],
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Invalid credentials"),
            403: OpenApiResponse(description="Account deactivated or no role"),
        },
    )
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
                'phone': mask_phone(user.phone),  # Masked for privacy
            }
        }, status=status.HTTP_200_OK)



@extend_schema(
    tags=["Auth"],
    responses={
        200: OpenApiResponse(
            description="Authenticated user info and role",
            response=inline_serializer(
                name="WhoAmIResponse",
                fields={
                    "id": serializers.IntegerField(),
                    "username": serializers.CharField(),
                    "phone": serializers.CharField(),
                    "role": serializers.CharField(),
                },
            ),
        ),
        403: OpenApiResponse(description="User has no assigned role"),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def whois(request: Request) -> Response:
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
        'phone': mask_phone(user.phone),  # Masked for privacy
        'role': role,
    }, status=status.HTTP_200_OK)


class SignupSerializer(serializers.Serializer):
    """
    Signup serializer validating Saudi phone numbers and passwords.
    
    Expected input:
    - name: string (used as username/display name)
    - phone: string in E.164-like format starting with +966 (e.g., +9665XXXXXXXX)
    - password: string, min 8 chars
    - password_confirm: string, must match password
    """
    name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_phone(self, value: str) -> str:
        import re
        raw = (value or "").strip()
        # Must start with +966 and followed by 9 digits (typically mobile 5XXXXXXXX)
        if not re.fullmatch(r"\+966\d{9}", raw):
            raise ValidationError("Phone must start with +966 and contain 9 digits after the country code.")
        # Store normalized numeric-only to be consistent with login normalization
        normalized = ''.join(ch for ch in raw if ch.isdigit())
        # Ensure uniqueness
        if User.objects.filter(phone=normalized).exists():
            raise ValidationError("Phone is already registered.")
        return normalized

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password_confirm"):
            raise ValidationError({"password_confirm": "Passwords do not match."})
        return attrs


class SignupView(APIView):
    """
    Public signup endpoint.
    
    POST /api/v1/auth/signup/
    Body: {"name": "...", "phone": "+9665XXXXXXXX", "password": "********", "password_confirm": "********"}
    Behavior:
    - Creates a new user with normalized phone
    - Assigns default role: Driver
    - Returns JWT tokens and user info
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                description="User created as Driver; tokens returned",
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "SignupSuccess",
                        value={
                            "access": "jwt-access-token",
                            "refresh": "jwt-refresh-token",
                            "role": "driver",
                            "user": {"id": 10, "username": "New Driver", "phone": "9665XXXXXXX"},
                        },
                    )
                ],
            ),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"].strip()
        phone_norm = serializer.validated_data["phone"]  # digits only
        password = serializer.validated_data["password"]

        # Generate a unique username fallback
        username_candidate = name or f"user_{phone_norm[-4:]}"
        if User.objects.filter(username=username_candidate).exists():
            username_candidate = f"{username_candidate}_{phone_norm[-4:]}"

        try:
            with transaction.atomic():
                user = User(username=username_candidate, phone=phone_norm, is_active=True)
                user.set_password(password)
                user.save()

                Driver.objects.create(user=user, is_active=True)
        except IntegrityError as exc:
            logger.exception("Signup failed due to integrity error", exc_info=exc)
            # Generic error message to avoid information disclosure
            error_msg = "User could not be created. The username or phone number may already be in use."
            raise ValidationError({"detail": error_msg})
        except ValidationError:
            # Re-raise validation errors as-is (they already have proper messages)
            raise
        except Exception as exc:
            logger.exception("Unexpected error during signup", exc_info=exc)
            # Generic error message - don't expose internal error details
            return Response(
                {"detail": "An error occurred while creating your account. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Issue tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        return Response({
            "access": str(access),
            "refresh": str(refresh),
            "role": "driver",
            "user": {
                "id": user.id,
                "username": user.username,
                "phone": mask_phone(user.phone),  # Masked for privacy
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Driver"],
    summary="عرض وتحديث حالة السائق (متاح/مشغول)",
    description="GET: يعرض الحالة الحالية للسائق. PATCH: يسمح للسائق بتحديث حالته من متاح (available) إلى مشغول (busy) والعكس.",
    methods=["GET"],
    responses={
        200: OpenApiResponse(
            description="الحالة الحالية للسائق",
            response=inline_serializer(
                name="DriverStatusResponse",
                fields={
                    "id": serializers.IntegerField(),
                    "username": serializers.CharField(),
                    "phone": serializers.CharField(),
                    "is_active": serializers.BooleanField(),
                    "status": serializers.CharField(help_text="متاح أو مشغول"),
                },
            ),
        ),
        403: OpenApiResponse(description="المستخدم ليس سائق أو لا يوجد ملف سائق"),
    },
)
@extend_schema(
    tags=["Driver"],
    summary="عرض وتحديث حالة السائق (متاح/مشغول)",
    description="GET: يعرض الحالة الحالية للسائق. PATCH: يسمح للسائق بتحديث حالته من متاح (available) إلى مشغول (busy) والعكس.",
    methods=["PATCH"],
    request=inline_serializer(
        name="DriverStatusUpdateRequest",
        fields={
            "is_active": serializers.BooleanField(
                help_text="True = متاح (available), False = مشغول (busy)"
            ),
        },
    ),
    responses={
        200: OpenApiResponse(
            description="تم تحديث الحالة بنجاح",
            response=inline_serializer(
                name="DriverStatusResponse",
                fields={
                    "id": serializers.IntegerField(),
                    "username": serializers.CharField(),
                    "phone": serializers.CharField(),
                    "is_active": serializers.BooleanField(),
                    "status": serializers.CharField(help_text="متاح أو مشغول"),
                },
            ),
        ),
        403: OpenApiResponse(description="المستخدم ليس سائق أو لا يوجد ملف سائق"),
        400: OpenApiResponse(description="بيانات غير صحيحة"),
    },
    examples=[
        OpenApiExample(
            "تحديث لمتاح",
            value={"is_active": True},
            request_only=True,
        ),
        OpenApiExample(
            "تحديث لمشغول",
            value={"is_active": False},
            request_only=True,
        ),
    ],
)
class DriverStatusUpdateView(APIView):
    """
    Endpoint لعرض وتحديث حالة السائق (متاح/مشغول).
    
    GET /api/v1/driver/status/ - يعرض الحالة الحالية
    PATCH /api/v1/driver/status/ - يحدث الحالة
    Body: {"is_active": true/false}
    Returns: {"id": 1, "username": "...", "phone": "...", "is_active": true/false, "status": "متاح/مشغول"}
    """
    permission_classes = [IsDriver]

    def get(self, request: Request) -> Response:
        """قراءة حالة السائق الحالية."""
        try:
            driver = Driver.objects.get(user=request.user)
        except Driver.DoesNotExist:
            logger.warning(f"Driver profile not found for user {request.user.id}")
            return Response(
                {"detail": "Driver profile not found. Please contact support if you believe this is an error."},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as exc:
            logger.exception(f"Unexpected error retrieving driver status for user {request.user.id}", exc_info=exc)
            return Response(
                {"detail": "An error occurred while retrieving your status. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        status_text = "متاح" if driver.is_active else "مشغول"

        return Response({
            "id": driver.user.id,
            "username": driver.user.username,
            "phone": mask_phone(driver.user.phone),  # Masked for privacy
            "is_active": driver.is_active,
            "status": status_text,
        }, status=status.HTTP_200_OK)

    def patch(self, request: Request) -> Response:
        """تحديث حالة السائق (is_active)."""
        try:
            driver = Driver.objects.get(user=request.user)
        except Driver.DoesNotExist:
            logger.warning(f"Driver profile not found for user {request.user.id}")
            return Response(
                {"detail": "Driver profile not found. Please contact support if you believe this is an error."},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as exc:
            logger.exception(f"Unexpected error retrieving driver for user {request.user.id}", exc_info=exc)
            return Response(
                {"detail": "An error occurred while processing your request. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        is_active = request.data.get("is_active")
        
        if is_active is None:
            return Response(
                {"detail": "is_active field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(is_active, bool):
            return Response(
                {"detail": "is_active must be a boolean value (true/false)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # تحديث الحالة
        driver.is_active = is_active
        driver.save(update_fields=["is_active"])
        
        # Invalidate driver status cache
        cache_key = f"driver_status_{driver.user.id}"
        cache.delete(cache_key)
        # Also invalidate drivers list cache
        try:
            # Try to delete cache keys (may fail if cache doesn't support keys())
            if hasattr(cache, 'keys'):
                keys = cache.keys("drivers_list_*")
                if keys:
                    cache.delete_many(keys)
        except (AttributeError, NotImplementedError):
            pass
        cache.delete("drivers_list")

        # تحديد حالة نصية للعرض
        status_text = "متاح" if is_active else "مشغول"

        logger.info(f"Driver {driver.user.username} updated status to {'available' if is_active else 'busy'}")

        return Response({
            "id": driver.user.id,
            "username": driver.user.username,
            "phone": mask_phone(driver.user.phone),  # Masked for privacy
            "is_active": driver.is_active,
            "status": status_text,
        }, status=status.HTTP_200_OK)

