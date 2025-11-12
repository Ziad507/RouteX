from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import RegexValidator




class Driver(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="driver_profile",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return f"Driver: {self.user.username}"


class WarehouseManager(models.Model):  
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="warehouse_manager_profile",
    )

    def __str__(self):
        phone = getattr(self.user, "phone", "")
        return f"WM: {self.user.username} ({phone})" if phone else f"WM: {self.user.username}"



class Product(models.Model):
    name= models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, blank=True, default='KG') 
    stock_qty = models.PositiveIntegerField(default=0)  # stock quantity 
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["location"]),
        ]
    def __str__(self):
        return self.name


class Customer(models.Model):
    # Saudi phone number validator (supports +966XXXXXXXXX format)
    saudi_phone_validator = RegexValidator(
        regex=r'^\+?966\d{9}$',
        message="Phone number must be a valid Saudi number starting with +966 or 966 followed by 9 digits."
    )
    
    name = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=20,
        validators=[saudi_phone_validator],
        help_text="Saudi phone number (e.g., +966512345678 or 966512345678)"
    )
    address = models.CharField(max_length=255, blank=True)
    address2 = models.CharField(max_length=255, blank=True)
    address3 = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["phone"]),
        ]
        ordering = ["name", "id"]  


    def __str__(self):
        return self.name


class ShipmentStatus(models.TextChoices):
    NEW = "NEW", "New"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_TRANSIT = "IN_TRANSIT", "In transit"
    DELIVERED = "DELIVERED", "Delivered"


# Status transition rules - defines allowed state changes
ALLOWED_STATUS_TRANSITIONS = {
    ShipmentStatus.NEW: [ShipmentStatus.ASSIGNED],
    ShipmentStatus.ASSIGNED: [ShipmentStatus.IN_TRANSIT, ShipmentStatus.NEW],  # Can reassign
    ShipmentStatus.IN_TRANSIT: [ShipmentStatus.DELIVERED, ShipmentStatus.ASSIGNED],  # Can go back if needed
    ShipmentStatus.DELIVERED: [],  # Final state - no transitions allowed
}


def validate_status_transition(old_status: str, new_status: str) -> bool:
    """
    Validate if a status transition is allowed.
    
    Args:
        old_status: Current shipment status
        new_status: Desired new status
        
    Returns:
        True if transition is allowed, False otherwise
        
    Raises:
        ValueError: If transition is not allowed
    """
    old_status = ShipmentStatus(old_status) if isinstance(old_status, str) else old_status
    new_status = ShipmentStatus(new_status) if isinstance(new_status, str) else new_status
    
    allowed = ALLOWED_STATUS_TRANSITIONS.get(old_status, [])
    
    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition: Cannot change from '{old_status.label}' "
            f"to '{new_status.label}'. Allowed transitions: {[s.label for s in allowed]}"
        )
    
    return True


class Shipment(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="shipments", null=True, blank=True
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="shipments"
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.PROTECT, related_name="shipments", null=True, blank=True
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="shipments", null=True, blank=True
    )
    customer_address = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, help_text="Number of product units in this shipment")
    notes = models.TextField(blank=True, null=True,default="")
    assigned_at = models.DateTimeField(default=timezone.now)
    current_status = models.CharField(max_length=20, default=ShipmentStatus.NEW, choices=ShipmentStatus.choices, db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Shipment#{self.pk} - {self.customer.name if self.customer else 'No Customer'}"



class StatusUpdate(models.Model):
    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE, related_name="status_updates"
    )
    status = models.CharField(max_length=20, choices=ShipmentStatus.choices, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    note = models.TextField(blank=True)
    photo = models.ImageField(upload_to="status_photos/", blank=True, null=True)
    location_accuracy_m = models.PositiveIntegerField(null=True, blank=True, help_text="GPS accuracy in meters.")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["status", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.shipment} -> {self.status} @ {self.timestamp:%Y-%m-%d %H:%M}"
