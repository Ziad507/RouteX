"""
Mixins for shipments views.

This module contains reusable mixins to eliminate code duplication
and improve code organization.
"""

from rest_framework.response import Response
from rest_framework import status
from .models import WarehouseManager


class WarehouseManagerQuerysetMixin:
    """
    Mixin to ensure queryset is filtered for warehouse managers only.
    
    Returns empty queryset if user is not a warehouse manager.
    This eliminates the need to repeat the check in every view.
    """
    
    def get_queryset(self):
        """
        Filter queryset to ensure only warehouse managers can access it.
        
        Returns:
            QuerySet: Filtered queryset or empty queryset if not manager
        """
        queryset = super().get_queryset()
        
        if not WarehouseManager.objects.filter(user=self.request.user).exists():
            return queryset.none()
        
        return queryset

