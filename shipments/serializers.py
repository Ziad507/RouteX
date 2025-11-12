from typing import Dict, Any, Optional, List
from rest_framework import serializers
from django.utils import timezone
from django.db import models
from django.core.cache import cache
from users.models import CustomUser
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import (
    WarehouseManager, Warehouse, Customer, Shipment,
    StatusUpdate, Driver, Product, validate_status_transition
)
from .constants import MAX_GPS_ACCURACY_METERS
from users.utils import mask_phone


# PRODUCTS
class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer with image upload support and validation.
    
    Handles:
    - Image upload with format and size validation
    - Stock quantity management
    - Shipment count tracking
    """
    shipments_count = serializers.IntegerField(read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "price", "unit", "stock_qty", "is_active",
            "image", "created_at", "shipments_count"
        ]
        read_only_fields = ["created_at", "shipments_count"]

    def validate_image(self, value: Any) -> Any:
        """
        Validate uploaded product image with comprehensive security checks.
        
        Checks:
        - File size (max 5MB)
        - File extension (jpg, jpeg, png, webp)
        - Actual file content (MIME type) - prevents file type spoofing
        """
        if not value:
            return value
        
        from django.conf import settings
        import os
        
        # Check file size
        max_size = getattr(settings, 'MAX_IMAGE_SIZE', 5 * 1024 * 1024)  # 5MB default
        
        if value.size > max_size:
            raise ValidationError(
                f"Image file too large. Maximum size is {max_size / (1024 * 1024):.1f}MB."
            )
        
        # Check file extension
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = getattr(
            settings, 
            'ALLOWED_IMAGE_EXTENSIONS', 
            ['.jpg', '.jpeg', '.png', '.webp']
        )
        
        if ext not in allowed_extensions:
            raise ValidationError(
                f"Invalid image format. Allowed formats: {', '.join(allowed_extensions)}"
            )
        
        # Validate actual file content (MIME type) to prevent file type spoofing
        try:
            from PIL import Image
            
            # Reset file pointer to beginning
            value.seek(0)
            
            # Try to open and verify the image
            try:
                img = Image.open(value)
                img.verify()  # Verify it's a valid image
                
                # Check if the actual format matches the extension
                actual_format = img.format.lower() if img.format else None
                format_map = {
                    'jpeg': ['.jpg', '.jpeg'],
                    'png': ['.png'],
                    'webp': ['.webp']
                }
                
                if actual_format and actual_format in format_map:
                    if ext not in format_map[actual_format]:
                        raise ValidationError(
                            f"File extension '{ext}' does not match actual image format '{actual_format}'. "
                            "This may indicate a security issue."
                        )
                
            except Exception as e:
                if isinstance(e, ValidationError):
                    raise
                raise ValidationError(
                    f"Invalid image file. The file cannot be opened as an image. "
                    f"Error: {str(e)}"
                )
            finally:
                # Reset file pointer for Django to save the file
                value.seek(0)
                
        except ImportError:
            # PIL not available - skip content validation (fallback)
            # In production, PIL should always be available
            pass
        
        return value

    def validate_price(self, value: float) -> float:
        """Ensure price is positive."""
        if value <= 0:
            raise ValidationError("Price must be greater than zero.")
        return value

    def validate_stock_qty(self, value: int) -> int:
        """Ensure stock quantity is non-negative."""
        if value < 0:
            raise ValidationError("Stock quantity cannot be negative.")
        return value



# SHIPMENTS
class ShipmentSerializer(serializers.ModelSerializer):
    # driver can be empty (shipment not yet assigned)
    driver = serializers.PrimaryKeyRelatedField(
        queryset=Driver.objects.all(), required=False, allow_null=True
    )
    driver_username = serializers.CharField(source="driver.user.username", read_only=True)
    customer_name   = serializers.CharField(source="customer.name", read_only=True)
    customer_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "warehouse",
            "product", "product_name",
            "driver", "driver_username",
            "customer", "customer_name",
            "customer_address",
            "quantity",
            "notes",
            "assigned_at",
            "current_status",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "created_at", "updated_at", "current_status",
            "driver_username", "customer_name", "product_name",
        ]

    def _customer_addresses_list(self, customer: Customer) -> List[str]:

        return [v for v in [
            getattr(customer, "address", None),
            getattr(customer, "address2", None),
            getattr(customer, "address3", None),
        ] if v]


    def _reserve_stock(self, product: Product, qty: int):
        """
        Reserve stock quantity from product inventory.
        
        Args:
            product: Product instance
            qty: Quantity to reserve (must be > 0)
        """
        if qty <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than zero."})
        
        updated = Product.objects.filter(
            pk=product.pk, stock_qty__gte=qty
        ).update(stock_qty=F("stock_qty") - qty)
        
        if updated == 0:
            available = Product.objects.get(pk=product.pk).stock_qty
            raise ValidationError({
                "product": f"Insufficient stock quantity. Available: {available}, Requested: {qty}."
            })

    def _release_stock(self, product: Product, qty: int) -> None:
        """
        Release stock quantity back to product inventory.
        
        Args:
            product: Product instance
            qty: Quantity to release (must be > 0)
        """
        if qty <= 0:
            return  # Nothing to release
        
        Product.objects.filter(pk=product.pk).update(stock_qty=F("stock_qty") + qty)

    # validation 
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        request = self.context["request"]
        if not WarehouseManager.objects.filter(user=request.user).exists():
            raise PermissionDenied("Only warehouse managers can create/update shipments.")

        # customer and address
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if not customer:
            attrs["customer_address"] = None
        else:
            allowed = self._customer_addresses_list(customer)
            if not allowed:
                raise ValidationError({"customer_address": "The customer has no saved addresses to use."})

            addr = attrs.get("customer_address", getattr(self.instance, "customer_address", None))
            addr_clean = None if addr is None else str(addr).strip()

            if not addr_clean:
                # Customer chosen but no address provided
                raise ValidationError({
                    "customer_address": "A customer has been selected. You must choose one of the customer's saved addresses.",
                    "allowed_addresses": allowed,
                })

            if addr_clean not in allowed:
                # Address must be one of the customer's addresses
                raise ValidationError({
                    "customer_address": "The address must be one of the customer's saved addresses.",
                    "allowed_addresses": allowed,
                })

            attrs["customer_address"] = addr_clean

        # Validate assigned_at is not in the future
        assigned_at = attrs.get("assigned_at")
        if assigned_at:
            now = timezone.now()
            if assigned_at > now:
                raise ValidationError({
                    "assigned_at": "Assigned date cannot be in the future. Please select a current or past date."
                })
        
        new_driver  = attrs.get("driver",  getattr(self.instance, "driver",  None))
        new_product = attrs.get("product", getattr(self.instance, "product", None))
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 1))

        # Validate quantity
        if quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than zero."})

        # Check driver availability
        if new_driver and not new_driver.is_active:
            raise ValidationError({
                "driver": f"Driver '{new_driver.user.username}' is currently busy/unavailable. Please select an available driver."
            })

        # check stock when assigning driver with product
        need_new_reservation = False
        if new_driver and new_product:
            if self.instance is None:
                need_new_reservation = True
            else:
                old_driver  = self.instance.driver
                old_product = self.instance.product
                if not old_driver:
                    # Previously no driver, now driver assigned
                    need_new_reservation = True
                elif old_product != new_product:
                    # Product changed while driver remains assigned
                    need_new_reservation = True

        if need_new_reservation and new_product:
            # Check if enough stock is available for the requested quantity
            if new_product.stock_qty < quantity:
                raise ValidationError({
                    "product": f"Insufficient available stock quantity. Available: {new_product.stock_qty}, Requested: {quantity}."
                })

        return attrs

    # create/update
    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> Shipment:
        # Create shipment, then reserve stock if both driver and product are assigned
        driver  = validated_data.get("driver")
        product = validated_data.get("product")
        quantity = validated_data.get("quantity", 1)

        obj = super().create(validated_data)

        if driver and product:
            self._reserve_stock(product, quantity)
        
        # Invalidate caches
        cache.delete("products_list")
        if product:
            cache.delete(f"product_{product.id}")
        cache.delete("drivers_list")
        if driver:
            cache.delete(f"driver_status_{driver.user.id}")

        return obj

    @transaction.atomic
    def update(self, instance: Shipment, validated_data: Dict[str, Any]) -> Shipment:
        # Update shipment and adjust stock when assignment (driver, product, quantity) changes.
        old_driver  = instance.driver
        old_product = instance.product
        old_quantity = instance.quantity

        new_driver  = validated_data.get("driver",  old_driver)
        new_product = validated_data.get("product", old_product)
        new_quantity = validated_data.get("quantity", old_quantity)

        obj = super().update(instance, validated_data)

        # Cases:
        if not old_driver and new_driver:
            # Driver assigned now
            if new_product:
                self._reserve_stock(new_product, new_quantity)

        elif old_driver and not new_driver:
            # Driver removed - release stock
            if old_product:
                self._release_stock(old_product, old_quantity)

        elif old_driver and new_driver:
            # Driver exists - check for product/quantity changes
            if old_product != new_product:
                # Product changed
                if old_product:
                    self._release_stock(old_product, old_quantity)
                if new_product:
                    self._reserve_stock(new_product, new_quantity)
            elif old_product == new_product and old_quantity != new_quantity:
                # Same product but quantity changed
                quantity_diff = new_quantity - old_quantity
                if quantity_diff > 0:
                    # Quantity increased - reserve more
                    self._reserve_stock(new_product, quantity_diff)
                else:
                    # Quantity decreased - release some
                    self._release_stock(new_product, abs(quantity_diff))
        
        # Invalidate caches
        cache.delete("products_list")
        if old_product:
            cache.delete(f"product_{old_product.id}")
        if new_product and new_product != old_product:
            cache.delete(f"product_{new_product.id}")
        cache.delete("drivers_list")
        if old_driver:
            cache.delete(f"driver_status_{old_driver.user.id}")
        if new_driver and new_driver != old_driver:
            cache.delete(f"driver_status_{new_driver.user.id}")

        return obj



# WAREHOUSE
class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "name", "location", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        request = self.context["request"]
        if not WarehouseManager.objects.filter(user=request.user).exists():
            raise PermissionDenied("Only warehouse managers can create/update warehouses.")

        # Normalize inputs 
        name     = (attrs.get("name",     getattr(self.instance, "name",     "")) or "").strip()
        location = (attrs.get("location", getattr(self.instance, "location", "")) or "").strip()

        if not name:
            raise ValidationError({"name": "Warehouse name is required."})
        if not location:
            raise ValidationError({"location": "Location/address is required."})

        attrs["name"] = name
        attrs["location"] = location

        # prevent duplicate name + location
        qs = Warehouse.objects.filter(name__iexact=name, location__iexact=location)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError({
                "non_field_errors": ["A warehouse with the same name and address already exists."]
            })

        return attrs



# CUSTOMERS
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Customer
        fields = ["id", "name", "phone", "address", "address2", "address3", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        request = self.context["request"]
        if not WarehouseManager.objects.filter(user=request.user).exists():
            raise PermissionDenied("Only warehouse managers can create/update customers.")

        addr  = (attrs.get("address")  or "").strip()
        addr2 = (attrs.get("address2") or "").strip()
        addr3 = (attrs.get("address3") or "").strip()

        if not (addr or addr2 or addr3):
            raise ValidationError({"addresses": "Provide at least one address."})

        # Prevent duplicate addresses for the same customer
        addresses_list = [a for a in [addr, addr2, addr3] if a]
        if len(addresses_list) != len(set(addresses_list)):
            raise ValidationError({
                "addresses": "Duplicate addresses are not allowed. Each address must be unique."
            })

        # Check for duplicate addresses across different customers (optional - can be removed if needed)
        # This prevents the same address from being used by multiple customers
        instance = getattr(self, 'instance', None)
        customer_id = instance.pk if instance else None
        
        # Check if any of the provided addresses already exist for another customer
        for address in addresses_list:
            existing_customer = Customer.objects.filter(
                models.Q(address=address) | 
                models.Q(address2=address) | 
                models.Q(address3=address)
            ).exclude(pk=customer_id).first()
            
            if existing_customer:
                raise ValidationError({
                    "addresses": f"The address '{address}' is already associated with another customer ({existing_customer.name})."
                })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key in ["address", "address2", "address3"]:
            if not data.get(key):
                data.pop(key, None)
        return data



# STATUS UPDATE (Driver)
class StatusUpdateSerializer(serializers.ModelSerializer):
    # Set by server at creation time
    timestamp = serializers.DateTimeField(read_only=True)
    customer_name  = serializers.CharField(source="shipment.customer.name",  read_only=True)
    customer_phone = serializers.SerializerMethodField()

    class Meta:
        model  = StatusUpdate
        fields = [
            "id",
            "shipment",
            "customer_name", "customer_phone",
            "status",
            "timestamp",
            "note", "photo",
            "latitude", "longitude",
            "location_accuracy_m",
        ]

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        request = self.context["request"]

        # must be a driver with profile
        try:
            driver_profile = Driver.objects.get(user=request.user)
        except Driver.DoesNotExist:
            raise PermissionDenied("Only drivers can create status updates.")

        shipment: Shipment = attrs["shipment"]
        if not shipment.driver or shipment.driver_id != driver_profile.id:
            raise PermissionDenied("You can only update the status of your own shipment.")

        # Validate status transition
        new_status = attrs.get("status")
        if new_status:
            try:
                validate_status_transition(shipment.current_status, new_status)
            except ValueError as e:
                raise ValidationError({"status": str(e)})

        # GPS accuracy validation
        acc = attrs.get("location_accuracy_m")
        if acc is not None and acc > MAX_GPS_ACCURACY_METERS:
            raise serializers.ValidationError({
                "location_accuracy_m": f"GPS accuracy must be ≤ {MAX_GPS_ACCURACY_METERS} meters."
            })

        # both latitude and longitude must be provided together
        lat, lng = attrs.get("latitude"), attrs.get("longitude")
        if (lat is None) ^ (lng is None):
            raise serializers.ValidationError("Both latitude and longitude must be provided together.")
        return attrs

    def get_customer_phone(self, obj) -> str:
        """Return masked customer phone number for privacy."""
        if obj.shipment.customer:
            return mask_phone(obj.shipment.customer.phone)
        return None
    
    def create(self, validated_data: Dict[str, Any]) -> Shipment:
        """Set server timestamp and create the status update."""
        validated_data["timestamp"] = timezone.now()
        return super().create(validated_data)



# DRIVER STATUS (for manager dashboard)
class DriverStatusSerializer(serializers.ModelSerializer):
    """Serialize driver state for manager dashboards with explicit availability flags."""

    name = serializers.CharField(source="user.username", read_only=True)
    phone = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    last_seen_at = serializers.DateTimeField(read_only=True)
    current_active_shipment_id = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Driver
        fields = [
            "id",
            "name", "phone",
            "status",
            "is_active",
            "last_seen_at",
            "current_active_shipment_id",
        ]

    def get_phone(self, obj) -> str:
        """Return masked phone number for privacy."""
        return mask_phone(obj.user.phone)
    
    def get_status(self, obj) -> str:
        """
        Derive a human readable status:
        - Busy if the driver currently has an active shipment assigned.
        - Available if the driver marked themselves available (even without open shipments).
        - Unavailable otherwise.
        """
        if getattr(obj, "current_active_shipment_id", None):
            return "Busy"
        if getattr(obj, "is_active", False):
            return "Available"
        return "Unavailable"
