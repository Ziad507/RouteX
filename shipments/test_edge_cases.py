"""
Edge case tests for shipments.

Tests:
- Boundary conditions
- Error scenarios
- Race conditions
- Invalid state transitions
"""

import pytest
from rest_framework import status
from shipments.models import Shipment, ShipmentStatus, Product, Driver


@pytest.mark.django_db
@pytest.mark.edge_cases
class TestBoundaryConditions:
    """Test boundary conditions."""
    
    SHIPMENTS_URL = "/api/v1/shipments/"
    
    def test_zero_quantity_rejected(self, manager_client, product, warehouse, customer, driver_user):
        """Test that zero quantity is rejected."""
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 0
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantity" in response.data
    
    def test_negative_quantity_rejected(self, manager_client, product, warehouse, customer, driver_user):
        """Test that negative quantity is rejected."""
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": -1
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantity" in response.data
    
    def test_exact_stock_quantity_allowed(self, manager_client, product, warehouse, customer, driver_user):
        """Test that exact stock quantity is allowed."""
        # Set product stock to exact amount
        product.stock_qty = 10
        product.save()
        
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 10  # Exact stock
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify stock is now 0
        product.refresh_from_db()
        assert product.stock_qty == 0
    
    def test_insufficient_stock_rejected(self, manager_client, product, warehouse, customer, driver_user):
        """Test that insufficient stock is rejected."""
        product.stock_qty = 5
        product.save()
        
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 10  # More than available
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "product" in response.data
        assert "Insufficient" in str(response.data["product"])


@pytest.mark.django_db
@pytest.mark.edge_cases
class TestErrorScenarios:
    """Test error scenarios."""
    
    SHIPMENTS_URL = "/api/v1/shipments/"
    
    def test_create_shipment_with_nonexistent_product(self, manager_client, warehouse, customer, driver_user):
        """Test creating shipment with nonexistent product fails gracefully."""
        shipment_data = {
            "product": 99999,  # Non-existent ID
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 1
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_shipment_with_nonexistent_customer(self, manager_client, product, warehouse, driver_user):
        """Test creating shipment with nonexistent customer fails gracefully."""
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": 99999,  # Non-existent ID
            "customer_address": "Some address",
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 1
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_nonexistent_shipment(self, manager_client):
        """Test updating nonexistent shipment returns 404."""
        response = manager_client.patch(
            f"{self.SHIPMENTS_URL}99999/",
            {"quantity": 5}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_nonexistent_shipment(self, manager_client):
        """Test deleting nonexistent shipment returns 404."""
        response = manager_client.delete(f"{self.SHIPMENTS_URL}99999/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.edge_cases
class TestInvalidStateTransitions:
    """Test invalid state transitions."""
    
    STATUS_UPDATES_URL = "/api/v1/status-updates/"
    
    def test_skip_status_transition_fails(self, driver_client, shipment):
        """Test that skipping status transitions fails."""
        # Try to go from NEW directly to DELIVERED (skipping ASSIGNED and IN_TRANSIT)
        shipment.current_status = ShipmentStatus.NEW
        shipment.save()
        
        status_data = {
            "shipment": shipment.id,
            "status": ShipmentStatus.DELIVERED,
            "note": "Trying to skip steps"
        }
        response = driver_client.post(
            self.STATUS_UPDATES_URL,
            status_data,
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data
        assert "Invalid status transition" in str(response.data["status"])
    
    def test_reverse_status_transition_allowed(self, driver_client, shipment):
        """Test that some reverse transitions are allowed (e.g., IN_TRANSIT -> ASSIGNED)."""
        shipment.current_status = ShipmentStatus.IN_TRANSIT
        shipment.save()
        
        # Try to go back to ASSIGNED (should be allowed)
        status_data = {
            "shipment": shipment.id,
            "status": ShipmentStatus.ASSIGNED,
            "note": "Returning to assigned"
        }
        response = driver_client.post(
            self.STATUS_UPDATES_URL,
            status_data,
            format='multipart'
        )
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_final_status_cannot_change(self, driver_client, shipment):
        """Test that DELIVERED status cannot be changed."""
        shipment.current_status = ShipmentStatus.DELIVERED
        shipment.save()
        
        # Try to change from DELIVERED to any other status
        status_data = {
            "shipment": shipment.id,
            "status": ShipmentStatus.IN_TRANSIT,
            "note": "Trying to change delivered status"
        }
        response = driver_client.post(
            self.STATUS_UPDATES_URL,
            status_data,
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.edge_cases
class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""
    
    SHIPMENTS_URL = "/api/v1/shipments/"
    
    def test_concurrent_stock_reservation(self, manager_client, product, warehouse, customer, driver_user):
        """Test that concurrent stock reservations are handled correctly."""
        # Set initial stock
        product.stock_qty = 10
        product.save()
        
        # Create two shipments simultaneously (simulated by creating them quickly)
        shipment_data1 = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 6
        }
        shipment_data2 = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 6
        }
        
        # Create first shipment
        response1 = manager_client.post(self.SHIPMENTS_URL, shipment_data1)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create second shipment (should fail due to insufficient stock)
        response2 = manager_client.post(self.SHIPMENTS_URL, shipment_data2)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "Insufficient" in str(response2.data.get("product", ""))

