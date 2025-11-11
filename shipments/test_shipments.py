"""
Shipment management and stock reservation tests.

Covers:
- Shipment CRUD operations
- Stock reservation logic
- Driver assignment
- Permission enforcement
- Status updates
"""

import pytest
from rest_framework import status
from shipments.models import Shipment, Product, ShipmentStatus


@pytest.mark.api
class TestShipmentCreation:
    """Test shipment creation and stock reservation."""
    
    url = "/api/v1/shipments/"
    
    def test_manager_creates_shipment_without_driver(self, manager_client, product, warehouse, customer):
        """Test creating shipment without driver assignment (no stock reservation)."""
        initial_stock = product.stock_qty
        
        data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "notes": "Test shipment"
        }
        response = manager_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Stock should NOT be reserved without driver
        product.refresh_from_db()
        assert product.stock_qty == initial_stock
    
    def test_manager_creates_shipment_with_driver(self, manager_client, product, warehouse, customer, driver_user):
        """Test creating shipment with driver (stock should be reserved)."""
        from shipments.models import Driver
        driver = Driver.objects.get(user=driver_user)
        
        initial_stock = product.stock_qty
        
        data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": driver.id,
            "notes": "Assigned shipment"
        }
        response = manager_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Stock SHOULD be reserved with driver
        product.refresh_from_db()
        assert product.stock_qty == initial_stock - 1
    
    def test_cannot_create_shipment_insufficient_stock(self, manager_client, warehouse, customer, driver_user):
        """Test that shipment creation fails with insufficient stock."""
        from shipments.models import Driver
        driver = Driver.objects.get(user=driver_user)
        
        # Create product with 0 stock
        product = Product.objects.create(
            name="Out of Stock",
            price=50.00,
            stock_qty=0
        )
        
        data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": driver.id,
        }
        response = manager_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "stock" in str(response.data).lower()
    
    def test_customer_address_validation(self, manager_client, product, warehouse, customer):
        """Test that customer address must be from saved addresses."""
        data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": "Invalid Address",  # Not in customer's addresses
        }
        response = manager_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "address" in str(response.data).lower()
    
    def test_driver_cannot_create_shipment(self, driver_client, product, warehouse, customer):
        """Test that drivers cannot create shipments."""
        data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
        }
        response = driver_client.post(self.url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestShipmentUpdate:
    """Test shipment updates and stock adjustments."""
    
    def get_url(self, pk):
        return f"/api/v1/shipments/{pk}/"
    
    def test_assign_driver_reserves_stock(self, manager_client, product, warehouse, customer, driver_user):
        """Test that assigning driver to existing shipment reserves stock."""
        from shipments.models import Driver
        driver = Driver.objects.get(user=driver_user)
        
        # Create shipment without driver
        shipment = Shipment.objects.create(
            product=product,
            warehouse=warehouse,
            customer=customer,
            customer_address=customer.address
        )
        
        initial_stock = product.stock_qty
        
        # Assign driver
        data = {
            "product": product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": driver.id,
        }
        response = manager_client.put(self.get_url(shipment.id), data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Stock should be reserved
        product.refresh_from_db()
        assert product.stock_qty == initial_stock - 1
    
    def test_remove_driver_releases_stock(self, manager_client, shipment):
        """Test that removing driver releases reserved stock."""
        product = shipment.product
        initial_stock = product.stock_qty
        
        # Remove driver
        data = {
            "product": product.id,
            "warehouse": shipment.warehouse.id,
            "customer": shipment.customer.id,
            "customer_address": shipment.customer_address,
            "driver": None,  # Remove driver
        }
        response = manager_client.put(self.get_url(shipment.id), data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Stock should be released
        product.refresh_from_db()
        assert product.stock_qty == initial_stock + 1
    
    def test_change_product_adjusts_stock(self, manager_client, shipment, warehouse, customer, driver_user):
        """Test that changing product adjusts stock correctly."""
        old_product = shipment.product
        old_stock = old_product.stock_qty
        
        # Create new product
        new_product = Product.objects.create(
            name="New Product",
            price=75.00,
            stock_qty=30
        )
        new_stock = new_product.stock_qty
        
        # Change product
        data = {
            "product": new_product.id,
            "warehouse": warehouse.id,
            "customer": customer.id,
            "customer_address": customer.address,
            "driver": shipment.driver.id,
        }
        response = manager_client.put(self.get_url(shipment.id), data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Old product stock released, new product stock reserved
        old_product.refresh_from_db()
        new_product.refresh_from_db()
        assert old_product.stock_qty == old_stock + 1
        assert new_product.stock_qty == new_stock - 1


@pytest.mark.api
class TestShipmentDelete:
    """Test shipment deletion and stock release."""
    
    def get_url(self, pk):
        return f"/api/v1/shipments/{pk}/"
    
    def test_delete_shipment_releases_stock(self, manager_client, shipment):
        """Test that deleting shipment releases reserved stock."""
        product = shipment.product
        initial_stock = product.stock_qty
        
        response = manager_client.delete(self.get_url(shipment.id))
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Stock should be released
        product.refresh_from_db()
        assert product.stock_qty == initial_stock + 1


@pytest.mark.api
class TestDriverShipments:
    """Test driver's view of assigned shipments."""
    
    url = "/api/v1/driver/shipments/"
    
    def test_driver_sees_assigned_shipments(self, driver_client, shipment):
        """Test that driver can see their assigned shipments."""
        response = driver_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        assert response.data["results"][0]["id"] == shipment.id
    
    def test_driver_sees_only_own_shipments(self, driver_client, shipment, create_user):
        """Test that driver only sees their own shipments, not others."""
        # Create another driver with shipment
        from shipments.models import Driver
        other_user = create_user(username="other_driver", phone="0509999999")
        other_driver = Driver.objects.create(user=other_user)
        
        other_shipment = Shipment.objects.create(
            product=shipment.product,
            warehouse=shipment.warehouse,
            customer=shipment.customer,
            customer_address=shipment.customer_address,
            driver=other_driver
        )
        
        response = driver_client.get(self.url)
        
        shipment_ids = [s["id"] for s in response.data["results"]]
        assert shipment.id in shipment_ids
        assert other_shipment.id not in shipment_ids
    
    def test_manager_cannot_access_driver_endpoint(self, manager_client):
        """Test that managers cannot access driver endpoint."""
        response = manager_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
class TestShipmentModel:
    """Test Shipment model methods."""
    
    def test_shipment_string_representation(self, shipment):
        """Test __str__ method."""
        expected = f"Shipment#{shipment.pk} - {shipment.customer.name}"
        assert str(shipment) == expected
    
    def test_shipment_default_status(self, product, warehouse, customer):
        """Test that new shipment has NEW status by default."""
        shipment = Shipment.objects.create(
            product=product,
            warehouse=warehouse,
            customer=customer,
            customer_address=customer.address
        )
        assert shipment.current_status == ShipmentStatus.NEW

