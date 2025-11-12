"""
Constants for shipments app.

This module contains all constant values used across the shipments app
to avoid magic numbers and improve code maintainability.
"""

from .models import ShipmentStatus

# ============================================================================
# QUERY LIMITS
# ============================================================================

# Maximum number of shipments to return in manager list view
SHIPMENT_LIST_LIMIT = 500

# Maximum number of results for autocomplete endpoints
AUTOCOMPLETE_LIMIT = 20

# ============================================================================
# STATUS CONSTANTS
# ============================================================================

# Active shipment statuses (in progress)
ACTIVE_STATUSES = [ShipmentStatus.ASSIGNED, ShipmentStatus.IN_TRANSIT]

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

# GPS accuracy threshold (in meters)
MAX_GPS_ACCURACY_METERS = 30

# Default shipment quantity
DEFAULT_SHIPMENT_QUANTITY = 1

# ============================================================================
# STOCK MANAGEMENT
# ============================================================================

# Low stock threshold (warn when stock falls below this)
LOW_STOCK_THRESHOLD = 10

