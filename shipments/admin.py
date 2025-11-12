from django.contrib import admin
from django import forms
from .models import Driver, WarehouseManager, Warehouse, Customer, Shipment, StatusUpdate, Product


class DriverAdminForm(forms.ModelForm):
    """
    Form validation for Driver admin to prevent role conflicts.
    Ensures a user cannot be both a Driver and WarehouseManager simultaneously.
    """
    class Meta:
        model = Driver
        fields = ["user", "is_active"]

    def clean_user(self):
        """
        Validate that the selected user doesn't already have a WarehouseManager profile.
        """
        u = self.cleaned_data.get("user")
        if not u:
            return u
        
        # Check if user already has WarehouseManager profile
        if WarehouseManager.objects.filter(user=u).exists():
            raise forms.ValidationError(
                f"User '{u.username}' already has a Warehouse Manager profile. "
                "A user cannot be both a Driver and a Warehouse Manager."
            )
        return u

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Driver profiles.
    Provides search, filtering, and status management capabilities.
    """
    form = DriverAdminForm
    autocomplete_fields = ["user"]
    list_display = ("id", "user_username", "user_phone", "is_active", "get_status_badge")
    search_fields = ("user__username", "user__phone")
    list_filter = ("is_active",)
    list_editable = ("is_active",)  # Allow quick toggling of status
    readonly_fields = ("user",)  # Prevent changing user after creation
    
    def user_username(self, obj):
        """Display driver's username."""
        return obj.user.username
    user_username.short_description = "Username"
    
    def user_phone(self, obj):
        """Display driver's phone number."""
        return obj.user.phone
    user_phone.short_description = "Phone"
    
    def get_status_badge(self, obj):
        """Display driver status as a colored badge."""
        from django.utils.html import format_html
        if obj.is_active:
            return format_html(
                '<span style="background: #10b981; color: white; padding: 4px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: 600;">Available</span>'
            )
        return format_html(
            '<span style="background: #ef4444; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: 600;">Busy</span>'
        )
    get_status_badge.short_description = "Status"

class WarehouseManagerAdminForm(forms.ModelForm):
    """
    Form validation for WarehouseManager admin to prevent role conflicts.
    Ensures a user cannot be both a Driver and WarehouseManager simultaneously.
    """
    class Meta:
        model = WarehouseManager
        fields = ["user"]

    def clean_user(self):
        """
        Validate that the selected user doesn't already have a Driver profile.
        """
        u = self.cleaned_data.get("user")
        if not u:
            return u
        
        # Check if user already has Driver profile
        if Driver.objects.filter(user=u).exists():
            raise forms.ValidationError(
                f"User '{u.username}' already has a Driver profile. "
                "A user cannot be both a Driver and a Warehouse Manager."
            )
        return u

@admin.register(WarehouseManager)
class WarehouseManagerAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Warehouse Manager profiles.
    Provides search and filtering capabilities.
    """
    form = WarehouseManagerAdminForm
    autocomplete_fields = ["user"]
    list_display = ("id", "user_username", "user_phone", "get_role_badge")
    search_fields = ("user__username", "user__phone")
    readonly_fields = ("user",)  # Prevent changing user after creation
    
    def user_username(self, obj):
        """Display warehouse manager's username."""
        return obj.user.username
    user_username.short_description = "Username"
    
    def user_phone(self, obj):
        """Display warehouse manager's phone number."""
        return obj.user.phone
    user_phone.short_description = "Phone"
    
    def get_role_badge(self, obj):
        """Display role as a colored badge."""
        from django.utils.html import format_html
        return format_html(
            '<span style="background: #3b82f6; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: 600;">📦 Warehouse Manager</span>'
        )
    get_role_badge.short_description = "Role"

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "created_at")
    list_filter = ("location",)
    search_fields = ("name", "location")
    date_hierarchy = "created_at"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit", "price", "stock_qty", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "address")
    search_fields = ("name", "phone")
    list_per_page = 50


class ShipmentAdminForm(forms.ModelForm):
    customer_address = forms.ChoiceField(
        required=False,
        choices=[("", "Choose the client first—")],
        label="Customer address",
    )

    class Meta:
        model = Shipment
        fields = "__all__"

    def _get_customer(self):
        if self.instance and self.instance.pk and self.instance.customer_id:
            return self.instance.customer

        cid = self.initial.get("customer")
        if cid:
            try:
                return Customer.objects.get(pk=cid)
            except Customer.DoesNotExist:
                return None

        cid = self.data.get("customer")
        if cid:
            try:
                return Customer.objects.get(pk=cid)
            except Customer.DoesNotExist:
                return None
        return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cust = self._get_customer()
        addresses = []
        if cust:
            for a in (cust.address, getattr(cust, "address2", ""), getattr(cust, "address3", "")):
                a = (a or "").strip()
                if a and a not in addresses:
                    addresses.append(a)

        if addresses:
            self.fields["customer_address"].choices = [("", "choose")] + [(a, a) for a in addresses]
            if len(addresses) == 1:
                self.fields["customer_address"].initial = addresses[0]
        else:
            self.fields["customer_address"].choices = [("", "— Choose the client first—")]

    def clean(self):
        cleaned = super().clean()
        cust = cleaned.get("customer")
        addr = (cleaned.get("customer_address") or "").strip()

        if not cust:
            cleaned["customer_address"] = None
            return cleaned

        allowed = []
        for a in (cust.address, getattr(cust, "address2", ""), getattr(cust, "address3", "")):
            a = (a or "").strip()
            if a and a not in allowed:
                allowed.append(a)

        if not allowed:
            self.add_error("customer", "The selected customer has no saved addresses.")
            self.add_error("customer_address", "The shipment cannot be saved without a customer address.")
            return cleaned

        if len(allowed) == 1 and not addr:
            cleaned["customer_address"] = allowed[0]
            return cleaned

        if not addr:
            self.add_error("customer_address", "Please choose a customer address.")
            return cleaned

        if addr not in allowed:
            self.add_error("customer_address", "The address must be one of the customer's saved addresses.")
            return cleaned

        cleaned["customer_address"] = addr
        return cleaned


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    form = ShipmentAdminForm
    autocomplete_fields = ("product", "warehouse", "driver", "customer")

    list_display = ("id", "product", "warehouse", "driver", "customer",
                    "customer_address", "current_status", "created_at")
    list_filter = ("warehouse", "current_status")
    search_fields = ("id", "warehouse__name", "warehouse__location",
                     "customer__name", "customer_address", "product__name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        cid = request.GET.get("customer")
        if cid:
            initial["customer"] = cid
        return initial


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    autocomplete_fields = ["shipment"]
    list_display = ("shipment", "status", "timestamp")
    list_filter = ("status",)
    search_fields = ("shipment__id", "shipment__driver__user__username", "shipment__driver__user__phone")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
