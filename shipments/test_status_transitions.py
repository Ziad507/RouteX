"""
Tests for shipment status transition validation.

This module tests that status transitions follow the defined rules:
- NEW → ASSIGNED (allowed)
- ASSIGNED → IN_TRANSIT (allowed)
- ASSIGNED → NEW (allowed - reassignment)
- IN_TRANSIT → DELIVERED (allowed)
- IN_TRANSIT → ASSIGNED (allowed - going back)
- DELIVERED → any (not allowed - final state)
- Invalid transitions should be rejected
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from shipments.models import (
    Shipment, StatusUpdate, Driver, Product, Warehouse, Customer,
    ShipmentStatus, validate_status_transition, ALLOWED_STATUS_TRANSITIONS
)
from shipments.permissions import IsDriver

User = get_user_model()


@pytest.fixture
def driver_user(db):
    """Create a driver user for testing."""
    user = User.objects.create_user(
        username="test_driver",
        phone="966500000001",
        password="testpass123"
    )
    Driver.objects.create(user=user, is_active=True)
    return user


@pytest.fixture
def manager_user(db):
    """Create a warehouse manager user for testing."""
    from shipments.models import WarehouseManager
    user = User.objects.create_user(
        username="test_manager",
        phone="966500000002",
        password="testpass123"
    )
    WarehouseManager.objects.create(user=user)
    return user


@pytest.fixture
def test_shipment(db, manager_user):
    """Create a test shipment."""
    warehouse = Warehouse.objects.create(name="Test Warehouse", location="Test Location")
    product = Product.objects.create(name="Test Product", price=100.00, stock_qty=10)
    customer = Customer.objects.create(name="Test Customer", phone="966500000003", address="Test Address")
    
    shipment = Shipment.objects.create(
        warehouse=warehouse,
        product=product,
        customer=customer,
        customer_address="Test Address",
        current_status=ShipmentStatus.NEW
    )
    return shipment


@pytest.fixture
def driver_client(driver_user):
    """Create an authenticated API client for driver."""
    client = APIClient()
    client.force_authenticate(user=driver_user)
    return client


@pytest.mark.django_db
class TestStatusTransitionValidation:
    """Test the validate_status_transition function."""
    
    def test_new_to_assigned_allowed(self):
        """NEW → ASSIGNED should be allowed."""
        assert validate_status_transition(ShipmentStatus.NEW, ShipmentStatus.ASSIGNED) is True
    
    def test_assigned_to_in_transit_allowed(self):
        """ASSIGNED → IN_TRANSIT should be allowed."""
        assert validate_status_transition(ShipmentStatus.ASSIGNED, ShipmentStatus.IN_TRANSIT) is True
    
    def test_assigned_to_new_allowed(self):
        """ASSIGNED → NEW should be allowed (reassignment)."""
        assert validate_status_transition(ShipmentStatus.ASSIGNED, ShipmentStatus.NEW) is True
    
    def test_in_transit_to_delivered_allowed(self):
        """IN_TRANSIT → DELIVERED should be allowed."""
        assert validate_status_transition(ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED) is True
    
    def test_in_transit_to_assigned_allowed(self):
        """IN_TRANSIT → ASSIGNED should be allowed (going back)."""
        assert validate_status_transition(ShipmentStatus.IN_TRANSIT, ShipmentStatus.ASSIGNED) is True
    
    def test_delivered_to_any_not_allowed(self):
        """DELIVERED → any status should not be allowed."""
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_status_transition(ShipmentStatus.DELIVERED, ShipmentStatus.NEW)
        
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_status_transition(ShipmentStatus.DELIVERED, ShipmentStatus.ASSIGNED)
    
    def test_new_to_delivered_not_allowed(self):
        """NEW → DELIVERED should not be allowed (skipping steps)."""
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_status_transition(ShipmentStatus.NEW, ShipmentStatus.DELIVERED)
    
    def test_new_to_in_transit_not_allowed(self):
        """NEW → IN_TRANSIT should not be allowed (skipping ASSIGNED)."""
        with pytest.raises(ValueError, match="Invalid status transition"):
            validate_status_transition(ShipmentStatus.NEW, ShipmentStatus.IN_TRANSIT)
    
    def test_string_status_values(self):
        """Function should work with string status values."""
        assert validate_status_transition("NEW", "ASSIGNED") is True
        assert validate_status_transition("ASSIGNED", "IN_TRANSIT") is True


@pytest.mark.django_db
class TestStatusUpdateAPI:
    """Test status update API endpoints with transition validation."""
    
    def test_valid_transition_new_to_assigned(self, driver_client, test_shipment, driver_user):
        """Test valid transition: NEW → ASSIGNED."""
        # Assign driver to shipment
        test_shipment.driver = Driver.objects.get(user=driver_user)
        test_shipment.current_status = ShipmentStatus.ASSIGNED
        test_shipment.save()
        
        # Create status update
        url = "/api/v1/status-updates/"
        data = {
            "shipment": test_shipment.id,
            "status": ShipmentStatus.ASSIGNED,
            "note": "Shipment assigned"
        }
        
        response = driver_client.post(url, data, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_valid_transition_assigned_to_in_transit(self, driver_client, test_shipment, driver_user):
        """Test valid transition: ASSIGNED → IN_TRANSIT."""
        test_shipment.driver = Driver.objects.get(user=driver_user)
        test_shipment.current_status = ShipmentStatus.ASSIGNED
        test_shipment.save()
        
        url = "/api/v1/status-updates/"
        data = {
            "shipment": test_shipment.id,
            "status": ShipmentStatus.IN_TRANSIT,
            "note": "In transit"
        }
        
        response = driver_client.post(url, data, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_valid_transition_in_transit_to_delivered(self, driver_client, test_shipment, driver_user):
        """Test valid transition: IN_TRANSIT → DELIVERED."""
        test_shipment.driver = Driver.objects.get(user=driver_user)
        test_shipment.current_status = ShipmentStatus.IN_TRANSIT
        test_shipment.save()
        
        url = "/api/v1/status-updates/"
        data = {
            "shipment": test_shipment.id,
            "status": ShipmentStatus.DELIVERED,
            "note": "Delivered"
        }
        
        response = driver_client.post(url, data, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_invalid_transition_new_to_delivered(self, driver_client, test_shipment, driver_user):
        """Test invalid transition: NEW → DELIVERED (should fail)."""
        test_shipment.driver = Driver.objects.get(user=driver_user)
        test_shipment.current_status = ShipmentStatus.NEW
        test_shipment.save()
        
        url = "/api/v1/status-updates/"
        data = {
            "shipment": test_shipment.id,
            "status": ShipmentStatus.DELIVERED,
            "note": "Trying to skip steps"
        }
        
        response = driver_client.post(url, data, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data
        assert "Invalid status transition" in str(response.data["status"])
    
    def test_invalid_transition_delivered_to_any(self, driver_client, test_shipment, driver_user):
        """Test invalid transition: DELIVERED → ASSIGNED (should fail)."""
        test_shipment.driver = Driver.objects.get(user=driver_user)
        test_shipment.current_status = ShipmentStatus.DELIVERED
        test_shipment.save()
        
        url = "/api/v1/status-updates/"
        data = {
            "shipment": test_shipment.id,
            "status": ShipmentStatus.ASSIGNED,
            "note": "Trying to change delivered shipment"
        }
        
        response = driver_client.post(url, data, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data
    
    def test_invalid_transition_skipping_assigned(self, driver_client, test_shipment, driver_user):
        """Test invalid transition: NEW → IN_TRANSIT (skipping ASSIGNED)."""
        test_shipment.driver = Driver.objects.get(user=driver_user)
        test_shipment.current_status = ShipmentStatus.NEW
        test_shipment.save()
        
        url = "/api/v1/status-updates/"
        data = {
            "shipment": test_shipment.id,
            "status": ShipmentStatus.IN_TRANSIT,
            "note": "Trying to skip ASSIGNED"
        }
        
        response = driver_client.post(url, data, format='multipart')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data


@pytest.mark.django_db
class TestAllowedTransitionsConstant:
    """Test that ALLOWED_STATUS_TRANSITIONS constant is correctly defined."""
    
    def test_all_statuses_have_transitions_defined(self):
        """All statuses should have transitions defined (even if empty)."""
        for status_choice in ShipmentStatus:
            assert status_choice in ALLOWED_STATUS_TRANSITIONS
    
    def test_delivered_has_no_transitions(self):
        """DELIVERED should have no allowed transitions (final state)."""
        assert len(ALLOWED_STATUS_TRANSITIONS[ShipmentStatus.DELIVERED]) == 0
    
    def test_new_has_assigned_transition(self):
        """NEW should only allow transition to ASSIGNED."""
        allowed = ALLOWED_STATUS_TRANSITIONS[ShipmentStatus.NEW]
        assert len(allowed) == 1
        assert ShipmentStatus.ASSIGNED in allowed
    
    def test_assigned_has_multiple_transitions(self):
        """ASSIGNED should allow transitions to IN_TRANSIT and NEW."""
        allowed = ALLOWED_STATUS_TRANSITIONS[ShipmentStatus.ASSIGNED]
        assert ShipmentStatus.IN_TRANSIT in allowed
        assert ShipmentStatus.NEW in allowed
        assert len(allowed) == 2

