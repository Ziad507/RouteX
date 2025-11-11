"""
Product management tests.

Covers:
- Product CRUD operations
- Stock management
- Image upload validation
- Permission enforcement
"""

import pytest
from rest_framework import status
from shipments.models import Product
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.mark.api
class TestProductListCreate:
    """Test product listing and creation."""
    
    url = "/api/v1/products/"
    
    def test_manager_can_list_products(self, manager_client, product):
        """Test that managers can list products."""
        response = manager_client.get(self.url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1
        assert response.data["results"][0]["name"] == "Test Product"
    
    def test_driver_cannot_list_products(self, driver_client):
        """Test that drivers cannot list products."""
        response = driver_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_manager_can_create_product(self, manager_client):
        """Test successful product creation by manager."""
        data = {
            "name": "New Product",
            "price": 150.00,
            "unit": "KG",
            "stock_qty": 100,
            "is_active": True
        }
        response = manager_client.post(self.url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Product.objects.filter(name="New Product").exists()
    
    def test_create_product_invalid_price(self, manager_client):
        """Test product creation with invalid price."""
        data = {
            "name": "Invalid Product",
            "price": -10.00,  # Negative price
            "unit": "KG",
            "stock_qty": 10,
        }
        response = manager_client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_create_product_invalid_stock(self, manager_client):
        """Test product creation with negative stock."""
        data = {
            "name": "Invalid Stock",
            "price": 50.00,
            "unit": "KG",
            "stock_qty": -5,  # Negative stock
        }
        response = manager_client.post(self.url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
class TestProductDetail:
    """Test product detail, update, and delete."""
    
    def get_url(self, pk):
        return f"/api/v1/products/{pk}/"
    
    def test_manager_can_retrieve_product(self, manager_client, product):
        """Test product detail retrieval."""
        response = manager_client.get(self.get_url(product.id))
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Test Product"
        assert response.data["price"] == "100.00"
    
    def test_manager_can_update_product(self, manager_client, product):
        """Test product update."""
        data = {
            "name": "Updated Product",
            "price": 200.00,
            "unit": "KG",
            "stock_qty": 75,
            "is_active": True
        }
        response = manager_client.put(self.get_url(product.id), data)
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.name == "Updated Product"
        assert float(product.price) == 200.00
    
    def test_manager_can_partial_update_product(self, manager_client, product):
        """Test partial product update (PATCH)."""
        data = {"price": 125.00}
        response = manager_client.patch(self.get_url(product.id), data)
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert float(product.price) == 125.00
        assert product.name == "Test Product"  # Unchanged
    
    def test_manager_can_delete_unused_product(self, manager_client, product):
        """Test deleting product with no shipments."""
        response = manager_client.delete(self.get_url(product.id))
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Product.objects.filter(id=product.id).exists()
    
    def test_cannot_delete_product_with_shipments(self, manager_client, shipment):
        """Test that products with shipments cannot be deleted."""
        product = shipment.product
        response = manager_client.delete(self.get_url(product.id))
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert Product.objects.filter(id=product.id).exists()
    
    def test_driver_cannot_access_product_detail(self, driver_client, product):
        """Test that drivers cannot access product details."""
        response = driver_client.get(self.get_url(product.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.api
class TestProductImageUpload:
    """Test product image upload and validation."""
    
    url = "/api/v1/products/"
    
    def create_test_image(self, size=(100, 100), format='JPEG'):
        """Helper to create test image."""
        file = BytesIO()
        image = Image.new('RGB', size, color='red')
        image.save(file, format)
        file.seek(0)
        return file
    
    def test_upload_valid_image(self, manager_client):
        """Test uploading valid image with product."""
        image_file = self.create_test_image()
        image = SimpleUploadedFile(
            "test_product.jpg",
            image_file.read(),
            content_type="image/jpeg"
        )
        
        data = {
            "name": "Product with Image",
            "price": 100.00,
            "unit": "KG",
            "stock_qty": 10,
            "is_active": True,
            "image": image
        }
        
        response = manager_client.post(
            self.url, 
            data, 
            format='multipart'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        product = Product.objects.get(id=response.data["id"])
        assert product.image is not None


@pytest.mark.unit
class TestProductModel:
    """Test Product model methods and behavior."""
    
    def test_product_string_representation(self, product):
        """Test __str__ method."""
        assert str(product) == "Test Product"
    
    def test_product_ordering(self, db):
        """Test that products are ordered by creation date (newest first)."""
        p1 = Product.objects.create(name="First", price=10, stock_qty=5)
        p2 = Product.objects.create(name="Second", price=20, stock_qty=10)
        
        products = list(Product.objects.all())
        assert products[0] == p2  # Newest first
        assert products[1] == p1

