"""
Custom throttle classes for role-based rate limiting.

Provides different rate limits for:
- Warehouse Managers (high limits for bulk operations)
- Drivers (moderate limits for status updates)
- General authenticated users
"""

from rest_framework.throttling import UserRateThrottle
from .models import WarehouseManager, Driver


class ManagerRateThrottle(UserRateThrottle):
    """
    Throttle for warehouse managers with high rate limits.
    
    Managers need high limits for:
    - Bulk shipment creation
    - Frequent autocomplete queries
    - Dashboard refreshes
    """
    rate = '10000/hour'
    scope = 'manager'
    
    def allow_request(self, request, view):
        """Only apply throttle to managers."""
        if not request.user or not request.user.is_authenticated:
            return True
        
        # Check if user is a manager
        if WarehouseManager.objects.filter(user=request.user).exists():
            return super().allow_request(request, view)
        
        return True  # Not a manager, skip this throttle


class DriverRateThrottle(UserRateThrottle):
    """
    Throttle for drivers with moderate rate limits.
    
    Drivers need moderate limits for:
    - Status updates with photos
    - Viewing assigned shipments
    - GPS location updates
    """
    rate = '5000/hour'
    scope = 'driver'
    
    def allow_request(self, request, view):
        """Only apply throttle to drivers."""
        if not request.user or not request.user.is_authenticated:
            return True
        
        # Check if user is a driver
        if Driver.objects.filter(user=request.user).exists():
            return super().allow_request(request, view)
        
        return True  # Not a driver, skip this throttle


class BurstRateThrottle(UserRateThrottle):
    """
    Short-term burst protection.
    
    Prevents rapid-fire requests that could:
    - Overload the database
    - Create duplicate records
    - Cause race conditions
    """
    rate = '60/minute'
    scope = 'burst'

