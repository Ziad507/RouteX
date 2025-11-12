"""
Integration tests for shipment workflow.

Tests complete workflows:
- Create shipment -> Update status -> Deliver
- Create shipment -> Delete -> Stock release
- Manager creates shipment -> Driver updates status
"""

import pytest
from rest_framework import status
from shipments.models import Shipment, ShipmentStatus, StatusUpdate, Product, Driver


@pytest.mark.django_db
@pytest.mark.integration
class TestShipmentWorkflow:
    """Test complete shipment workflow."""
    
    SHIPMENTS_URL = "/api/v1/shipments/"
    STATUS_UPDATES_URL = "/api/v1/status-updates/"
    
    def test_create_shipment_to_delivery_flow(self, manager_client, product, warehouse, customer, driver_user):
        """Test complete flow: create -> assign -> in_transit -> delivered."""
        # 1. Create shipment
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 5
        }
        create_response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        shipment_id = create_response.data["id"]
        
        # Verify stock was reserved
        product.refresh_from_db()
        assert product.stock_qty == 45  # 50 - 5
        
        # 2. Driver updates status to IN_TRANSIT
        driver = Driver.objects.get(user=driver_user)
        driver_client = manager_client  # Using manager client for now
        driver_client.force_authenticate(user=driver_user)
        
        status_data = {
            "shipment": shipment_id,
            "status": ShipmentStatus.IN_TRANSIT,
            "note": "On the way"
        }
        status_response = driver_client.post(
            self.STATUS_UPDATES_URL,
            status_data,
            format='multipart'
        )
        assert status_response.status_code == status.HTTP_201_CREATED
        
        # Verify shipment status updated
        shipment = Shipment.objects.get(id=shipment_id)
        assert shipment.current_status == ShipmentStatus.IN_TRANSIT
        
        # 3. Driver updates status to DELIVERED
        status_data2 = {
            "shipment": shipment_id,
            "status": ShipmentStatus.DELIVERED,
            "note": "Delivered successfully"
        }
        status_response2 = driver_client.post(
            self.STATUS_UPDATES_URL,
            status_data2,
            format='multipart'
        )
        assert status_response2.status_code == status.HTTP_201_CREATED
        
        # Verify final status
        shipment.refresh_from_db()
        assert shipment.current_status == ShipmentStatus.DELIVERED
        
        # Verify status updates were created
        assert StatusUpdate.objects.filter(shipment=shipment).count() == 2
    
    def test_create_delete_shipment_stock_management(self, manager_client, product, warehouse, customer, driver_user):
        """Test that stock is properly managed when creating and deleting shipments."""
        initial_stock = product.stock_qty
        
        # 1. Create shipment
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 10
        }
        create_response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        shipment_id = create_response.data["id"]
        
        # Verify stock was reserved
        product.refresh_from_db()
        assert product.stock_qty == initial_stock - 10
        
        # 2. Delete shipment
        delete_response = manager_client.delete(f"{self.SHIPMENTS_URL}{shipment_id}/")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify stock was released
        product.refresh_from_db()
        assert product.stock_qty == initial_stock
    
    def test_shipment_quantity_update_stock_management(self, manager_client, product, warehouse, customer, driver_user):
        """Test stock management when updating shipment quantity."""
        initial_stock = product.stock_qty
        
        # 1. Create shipment with quantity 5
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": Driver.objects.get(user=driver_user).id,
            "quantity": 5
        }
        create_response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        shipment_id = create_response.data["id"]
        
        # Verify stock reserved
        product.refresh_from_db()
        assert product.stock_qty == initial_stock - 5
        
        # 2. Update quantity to 8 (increase by 3)
        update_data = {"quantity": 8}
        update_response = manager_client.patch(
            f"{self.SHIPMENTS_URL}{shipment_id}/",
            update_data
        )
        assert update_response.status_code == status.HTTP_200_OK
        
        # Verify additional stock reserved
        product.refresh_from_db()
        assert product.stock_qty == initial_stock - 8
        
        # 3. Update quantity to 3 (decrease by 5)
        update_data2 = {"quantity": 3}
        update_response2 = manager_client.patch(
            f"{self.SHIPMENTS_URL}{shipment_id}/",
            update_data2
        )
        assert update_response2.status_code == status.HTTP_200_OK
        
        # Verify stock released
        product.refresh_from_db()
        assert product.stock_qty == initial_stock - 3


@pytest.mark.django_db
@pytest.mark.integration
class TestManagerDriverInteraction:
    """Test interaction between manager and driver."""
    
    SHIPMENTS_URL = "/api/v1/shipments/"
    DRIVERS_URL = "/api/v1/drivers/"
    DRIVER_STATUS_URL = "/api/v1/driver/status/"
    
    def test_manager_sees_driver_status_update(self, manager_client, driver_client, driver_user):
        """Test that manager sees driver status changes in real-time."""
        # 1. Manager checks driver status (should be available)
        drivers_response = manager_client.get(self.DRIVERS_URL)
        assert drivers_response.status_code == status.HTTP_200_OK
        driver_data = drivers_response.data["results"][0]
        assert driver_data["is_active"] is True
        assert driver_data["status"] == "Available"
        
        # 2. Driver updates status to busy
        driver_update_response = driver_client.patch(
            self.DRIVER_STATUS_URL,
            {"is_active": False}
        )
        assert driver_update_response.status_code == status.HTTP_200_OK
        
        # 3. Manager checks again (should see updated status)
        drivers_response2 = manager_client.get(self.DRIVERS_URL)
        driver_data2 = drivers_response2.data["results"][0]
        assert driver_data2["is_active"] is False
        assert driver_data2["status"] == "Unavailable"
    
    def test_manager_assigns_shipment_to_available_driver(self, manager_client, product, warehouse, customer, driver_user):
        """Test manager can assign shipment to available driver."""
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = True
        driver.save()
        
        # Create shipment
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": driver.id,
            "quantity": 1
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_manager_cannot_assign_to_unavailable_driver(self, manager_client, product, warehouse, customer, driver_user):
        """Test manager cannot assign shipment to unavailable driver."""
        driver = Driver.objects.get(user=driver_user)
        driver.is_active = False
        driver.save()
        
        # Try to create shipment
        shipment_data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": driver.id,
            "quantity": 1
        }
        response = manager_client.post(self.SHIPMENTS_URL, shipment_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "driver" in response.data
        assert "busy/unavailable" in str(response.data["driver"]).lower()

