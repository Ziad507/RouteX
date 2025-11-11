"""
Pytest configuration and shared fixtures.

Provides:
- Database fixtures
- User and role fixtures
- API client fixtures
- Common test data
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from shipments.models import (
    Driver, WarehouseManager, Product, Warehouse, 
    Customer, Shipment, ShipmentStatus
)

User = get_user_model()


@pytest.fixture
def api_client(db):
    """Return unauthenticated API client with DB access enabled."""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory for creating users."""
    def _create_user(username="testuser", phone="0500000000", password="testpass123", **kwargs):
        user = User.objects.create_user(
            username=username,
            phone=phone,
            password=password,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def manager_user(create_user):
    """Create warehouse manager user with profile."""
    user = create_user(username="manager", phone="0501111111")
    WarehouseManager.objects.create(user=user)
    return user


@pytest.fixture
def driver_user(create_user):
    """Create driver user with profile."""
    user = create_user(username="driver", phone="0502222222")
    Driver.objects.create(user=user, is_active=True)
    return user


@pytest.fixture
def manager_client(api_client, manager_user):
    """Return API client authenticated as manager."""
    api_client.force_authenticate(user=manager_user)
    return api_client


@pytest.fixture
def driver_client(api_client, driver_user):
    """Return API client authenticated as driver."""
    api_client.force_authenticate(user=driver_user)
    return api_client


@pytest.fixture
def product(db):
    """Create sample product."""
    return Product.objects.create(
        name="Test Product",
        price=100.00,
        unit="KG",
        stock_qty=50,
        is_active=True
    )


@pytest.fixture
def warehouse(db):
    """Create sample warehouse."""
    return Warehouse.objects.create(
        name="Main Warehouse",
        location="Riyadh, KSA"
    )


@pytest.fixture
def customer(db):
    """Create sample customer."""
    return Customer.objects.create(
        name="Test Customer",
        phone="0503333333",
        address="Riyadh, Street 1",
        address2="Riyadh, Street 2"
    )


@pytest.fixture
def shipment(db, product, warehouse, customer, driver_user):
    """Create sample shipment."""
    driver = Driver.objects.get(user=driver_user)
    return Shipment.objects.create(
        product=product,
        warehouse=warehouse,
        customer=customer,
        customer_address=customer.address,
        driver=driver,
        current_status=ShipmentStatus.ASSIGNED,
        notes="Test shipment"
    )

