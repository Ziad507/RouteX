"""
Tests for shipment quantity and driver availability features.

This module tests:
- Quantity field validation and stock management
- Driver availability check before assignment
- Stock reservation/release with different quantities
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from shipments.models import (
    Shipment, Driver, Product, Warehouse, Customer, ShipmentStatus
)
from shipments.models import WarehouseManager

User = get_user_model()


@pytest.fixture
def manager_user(db):
    """Create a warehouse manager user for testing."""
    user = User.objects.create_user(
        username="test_manager",
        phone="966500000010",
        password="testpass123"
    )
    WarehouseManager.objects.create(user=user)
    return user


@pytest.fixture
def available_driver(db):
    """Create an available driver."""
    user = User.objects.create_user(
        username="available_driver",
        phone="966500000011",
        password="testpass123"
    )
    driver = Driver.objects.create(user=user, is_active=True)
    return driver


@pytest.fixture
def busy_driver(db):
    """Create a busy (unavailable) driver."""
    user = User.objects.create_user(
        username="busy_driver",
        phone="966500000012",
        password="testpass123"
    )
    driver = Driver.objects.create(user=user, is_active=False)
    return driver


@pytest.fixture
def test_product(db):
    """Create a test product with stock."""
    return Product.objects.create(
        name="Test Product",
        price=100.00,
        stock_qty=50  # 50 units available
    )


@pytest.fixture
def test_warehouse(db):
    """Create a test warehouse."""
    return Warehouse.objects.create(
        name="Test Warehouse",
        location="Test Location"
    )


@pytest.fixture
def test_customer(db):
    """Create a test customer."""
    return Customer.objects.create(
        name="Test Customer",
        phone="966500000013",
        address="Test Address"
    )


@pytest.fixture
def manager_client(manager_user):
    """Create an authenticated API client for manager."""
    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


@pytest.mark.django_db
class TestQuantityField:
    """Test quantity field functionality."""
    
    def test_create_shipment_with_quantity(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test creating a shipment with quantity > 1."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": available_driver.id,
            "quantity": 5
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["quantity"] == 5
        
        # Check stock was reduced by 5
        test_product.refresh_from_db()
        assert test_product.stock_qty == 45  # 50 - 5 = 45
    
    def test_create_shipment_with_default_quantity(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test creating a shipment without specifying quantity (should default to 1)."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": available_driver.id,
            # quantity not specified
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["quantity"] == 1  # Default value
        
        # Check stock was reduced by 1
        test_product.refresh_from_db()
        assert test_product.stock_qty == 49  # 50 - 1 = 49
    
    def test_create_shipment_with_zero_quantity_fails(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test that quantity must be > 0."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": available_driver.id,
            "quantity": 0
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantity" in response.data
    
    def test_create_shipment_with_negative_quantity_fails(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test that quantity cannot be negative."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": available_driver.id,
            "quantity": -5
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantity" in response.data
    
    def test_create_shipment_with_insufficient_stock_fails(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test that creating shipment with quantity > available stock fails."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": available_driver.id,
            "quantity": 100  # More than available (50)
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "product" in response.data
        assert "Insufficient" in str(response.data["product"])


@pytest.mark.django_db
class TestDriverAvailability:
    """Test driver availability validation."""
    
    def test_assign_available_driver_succeeds(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test assigning an available driver succeeds."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": available_driver.id,
            "quantity": 1
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_assign_busy_driver_fails(self, manager_client, test_product, test_warehouse, test_customer, busy_driver):
        """Test assigning a busy driver fails."""
        url = "/api/v1/shipments/"
        data = {
            "product": test_product.id,
            "warehouse": test_warehouse.id,
            "customer": test_customer.id,
            "customer_address": "Test Address",
            "driver": busy_driver.id,
            "quantity": 1
        }
        
        response = manager_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "driver" in response.data
        assert "busy" in str(response.data["driver"]).lower() or "unavailable" in str(response.data["driver"]).lower()
    
    def test_update_shipment_to_busy_driver_fails(self, manager_client, test_product, test_warehouse, test_customer, available_driver, busy_driver):
        """Test updating shipment to assign busy driver fails."""
        # Create shipment with available driver
        shipment = Shipment.objects.create(
            product=test_product,
            warehouse=test_warehouse,
            customer=test_customer,
            customer_address="Test Address",
            driver=available_driver,
            quantity=1,
            current_status=ShipmentStatus.NEW
        )
        
        # Try to update to busy driver
        url = f"/api/v1/shipments/{shipment.id}/"
        data = {
            "driver": busy_driver.id
        }
        
        response = manager_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "driver" in response.data


@pytest.mark.django_db
class TestQuantityStockManagement:
    """Test stock management with different quantities."""
    
    def test_update_quantity_increases_stock_reservation(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test increasing quantity reserves more stock."""
        # Create shipment with quantity=2
        shipment = Shipment.objects.create(
            product=test_product,
            warehouse=test_warehouse,
            customer=test_customer,
            customer_address="Test Address",
            driver=available_driver,
            quantity=2,
            current_status=ShipmentStatus.NEW
        )
        
        initial_stock = test_product.stock_qty
        assert initial_stock == 48  # 50 - 2 = 48
        
        # Update quantity to 5
        url = f"/api/v1/shipments/{shipment.id}/"
        data = {"quantity": 5}
        
        response = manager_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        # Check stock: 48 - 3 (additional) = 45
        test_product.refresh_from_db()
        assert test_product.stock_qty == 45
    
    def test_update_quantity_decreases_stock_reservation(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test decreasing quantity releases stock."""
        # Create shipment with quantity=5
        shipment = Shipment.objects.create(
            product=test_product,
            warehouse=test_warehouse,
            customer=test_customer,
            customer_address="Test Address",
            driver=available_driver,
            quantity=5,
            current_status=ShipmentStatus.NEW
        )
        
        initial_stock = test_product.stock_qty
        assert initial_stock == 45  # 50 - 5 = 45
        
        # Update quantity to 2
        url = f"/api/v1/shipments/{shipment.id}/"
        data = {"quantity": 2}
        
        response = manager_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        # Check stock: 45 + 3 (released) = 48
        test_product.refresh_from_db()
        assert test_product.stock_qty == 48
    
    def test_delete_shipment_releases_stock(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test deleting shipment releases reserved stock."""
        # Create shipment with quantity=10
        shipment = Shipment.objects.create(
            product=test_product,
            warehouse=test_warehouse,
            customer=test_customer,
            customer_address="Test Address",
            driver=available_driver,
            quantity=10,
            current_status=ShipmentStatus.NEW
        )
        
        initial_stock = test_product.stock_qty
        assert initial_stock == 40  # 50 - 10 = 40
        
        # Delete shipment
        url = f"/api/v1/shipments/{shipment.id}/"
        response = manager_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Check stock: 40 + 10 (released) = 50
        test_product.refresh_from_db()
        assert test_product.stock_qty == 50
    
    def test_remove_driver_releases_stock(self, manager_client, test_product, test_warehouse, test_customer, available_driver):
        """Test removing driver releases stock."""
        # Create shipment with driver and quantity=3
        shipment = Shipment.objects.create(
            product=test_product,
            warehouse=test_warehouse,
            customer=test_customer,
            customer_address="Test Address",
            driver=available_driver,
            quantity=3,
            current_status=ShipmentStatus.NEW
        )
        
        initial_stock = test_product.stock_qty
        assert initial_stock == 47  # 50 - 3 = 47
        
        # Remove driver
        url = f"/api/v1/shipments/{shipment.id}/"
        data = {"driver": None}
        
        response = manager_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        # Check stock: 47 + 3 (released) = 50
        test_product.refresh_from_db()
        assert test_product.stock_qty == 50

