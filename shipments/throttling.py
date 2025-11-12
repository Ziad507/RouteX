"""
Custom throttling classes for enhanced API security.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, ScopedRateThrottle
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


class IPRateThrottle(AnonRateThrottle):
    """
    Throttle based on IP address for anonymous users.
    Useful for preventing abuse from specific IPs.
    """
    scope = 'anon'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on IP address.
        """
        if request.user.is_authenticated:
            return None  # Don't throttle authenticated users with IP throttling
        
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class CustomUserRateThrottle(UserRateThrottle):
    """
    Enhanced user rate throttle with better caching.
    """
    scope = 'user'
    
    def get_cache_key(self, request, view):
        """
        Generate cache key based on user ID.
        """
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class DriverRateThrottle(UserRateThrottle):
    """
    Custom throttle for drivers - higher limits for status updates.
    """
    scope = 'driver'


class ManagerRateThrottle(UserRateThrottle):
    """
    Custom throttle for warehouse managers - highest limits.
    """
    scope = 'manager'


class SensitiveEndpointThrottle(UserRateThrottle):
    """
    Stricter throttling for sensitive endpoints (login, signup, etc.).
    """
    scope = 'sensitive'
    
    def get_cache_key(self, request, view):
        """
        Use IP address for sensitive endpoints to prevent abuse.
        """
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
