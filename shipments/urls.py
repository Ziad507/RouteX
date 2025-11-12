"""
Shipments app URL configuration.

API versioning: v1
All endpoints use consistent trailing slash convention.
"""

from django.urls import path
from shipments.views import (
    ShipmentCreateView, ShipmentDetailView,
    DriverShipmentsList,
    StatusUpdateCreateView, WarehouseListCreateView, WarehouseDetailView, 
    CustomerListCreateView, CustomerDetailView, CustomerAddressesView,
    ShipmentsListView, AutocompleteShipmentsView, AutocompleteCustomersView,
    DriverStatusView, DriverDetailManagerView, ProductListCreateView, ProductDetailView,
)

# API version prefix
API_PREFIX = "api/v1"

urlpatterns = [
    # ============================================================================
    # PRODUCT ENDPOINTS (Warehouse Manager only)
    # ============================================================================
    path(f"{API_PREFIX}/products/", ProductListCreateView.as_view(), name="product-list-create"),
    path(f"{API_PREFIX}/products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),

    # ============================================================================
    # SHIPMENT ENDPOINTS
    # ============================================================================
    # Manager: create, update, delete shipments
    path(f"{API_PREFIX}/shipments/", ShipmentCreateView.as_view(), name="shipment-create"),
    path(f"{API_PREFIX}/shipments/<int:pk>/", ShipmentDetailView.as_view(), name="shipment-detail"),
    
    # Manager: list all shipments with filters
    path(f"{API_PREFIX}/manager/shipments/", ShipmentsListView.as_view(), name="manager-shipments-list"),
    
    # Driver: list assigned shipments
    path(f"{API_PREFIX}/driver/shipments/", DriverShipmentsList.as_view(), name="driver-shipments-list"),

    # ============================================================================
    # STATUS UPDATE ENDPOINTS (Driver only)
    # ============================================================================
    path(f"{API_PREFIX}/status-updates/", StatusUpdateCreateView.as_view(), name="status-update-create"),

    # ============================================================================
    # WAREHOUSE ENDPOINTS (Manager only)
    # ============================================================================
    path(f"{API_PREFIX}/warehouses/", WarehouseListCreateView.as_view(), name="warehouse-list-create"),
    path(f"{API_PREFIX}/warehouses/<int:pk>/", WarehouseDetailView.as_view(), name="warehouse-detail"),

    # ============================================================================
    # CUSTOMER ENDPOINTS (Manager only)
    # ============================================================================
    path(f"{API_PREFIX}/customers/", CustomerListCreateView.as_view(), name="customer-list-create"),
    path(f"{API_PREFIX}/customers/<int:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
    path(f"{API_PREFIX}/customers/<int:pk>/addresses/", CustomerAddressesView.as_view(), name="customer-addresses"),

    # ============================================================================
    # DRIVER MANAGEMENT ENDPOINTS (Manager only)
    # ============================================================================
    path(f"{API_PREFIX}/drivers/", DriverStatusView.as_view({"get": "list"}), name="driver-status-list"),
    path(f"{API_PREFIX}/drivers/<int:pk>/", DriverDetailManagerView.as_view(), name="driver-detail"),

    # ============================================================================
    # AUTOCOMPLETE ENDPOINTS (Manager only)
    # ============================================================================
    path(f"{API_PREFIX}/autocomplete/shipments/", AutocompleteShipmentsView.as_view(), name="autocomplete-shipments"),
    path(f"{API_PREFIX}/autocomplete/customers/", AutocompleteCustomersView.as_view(), name="autocomplete-customers"),
]
