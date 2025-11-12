from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q, F
from .models import Driver, WarehouseManager, Warehouse, Customer, Shipment, StatusUpdate, Product


# ============================================================================
# DRIVER ADMIN
# ============================================================================

class DriverAdminForm(forms.ModelForm):
    """Enhanced form with role conflict validation."""
    
    class Meta:
        model = Driver
        fields = ["user", "is_active"]
    
    def clean_user(self):
        """Prevent driver/manager role conflicts."""
        u = self.cleaned_data.get("user")
        if not u:
            return u
        
        if WarehouseManager.objects.filter(user=u).exists():
            raise forms.ValidationError(
                f"⚠ User '{u.username}' is already a Warehouse Manager. "
                "A user cannot have both roles simultaneously."
            )
        return u


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    """
    Comprehensive Driver management with status tracking.
    
    Features:
    - Visual status indicators (Available/Busy)
    - Quick status toggle
    - Shipment count tracking
    - Advanced search by user details
    """
    
    form = DriverAdminForm
    autocomplete_fields = ["user"]
    
    list_display = (
        "id",
        "get_driver_name",
        "get_driver_phone",
        "get_status_badge",
        "get_shipments_info",
        "get_actions",
    )
    
    list_display_links = ("id", "get_driver_name")
    list_filter = ("is_active",)
    search_fields = ("user__username", "user__phone", "user__first_name", "user__last_name")
    list_per_page = 25
    
    fieldsets = (
        ("👤 Driver Information", {
            "fields": ("user",),
            "description": "Select the user account for this driver profile.",
        }),
        ("📊 Status", {
            "fields": ("is_active",),
            "description": "✅ Available: Driver can accept new shipments | ⏸ Busy: Driver is currently occupied",
        }),
    )
    
    readonly_fields = ()
    
    def get_queryset(self, request):
        """Optimize with shipment counting."""
        qs = super().get_queryset(request)
        qs = qs.select_related('user').annotate(
            total_shipments=Count('shipment'),
            active_shipments=Count(
                'shipment',
                filter=Q(shipment__current_status__in=['ASSIGNED', 'IN_TRANSIT'])
            )
        )
        return qs
    
    def get_driver_name(self, obj):
        """Display driver name with icon."""
        return format_html(
            '<strong>🚗 {}</strong>',
            obj.user.username
        )
    
    get_driver_name.short_description = "Driver Name"
    get_driver_name.admin_order_field = "user__username"
    
    def get_driver_phone(self, obj):
        """Display formatted phone number."""
        return format_html(
            '<span style="color: #64748b;">📞 {}</span>',
            obj.user.phone
        )
    
    get_driver_phone.short_description = "Phone"
    get_driver_phone.admin_order_field = "user__phone"
    
    def get_status_badge(self, obj):
        """Enhanced status badge with toggle hint."""
        if obj.is_active:
            return format_html(
                '<span style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); '
                'color: white; padding: 6px 14px; border-radius: 20px; font-size: 11px; '
                'font-weight: 600; box-shadow: 0 2px 10px rgba(16,185,129,0.3); '
                'cursor: pointer;" title="Click to toggle">✓ Available</span>'
            )
        return format_html(
            '<span style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); '
            'color: white; padding: 6px 14px; border-radius: 20px; font-size: 11px; '
            'font-weight: 600; box-shadow: 0 2px 10px rgba(239,68,68,0.3); '
            'cursor: pointer;" title="Click to toggle">⏸ Busy</span>'
        )
    
    get_status_badge.short_description = "📊 Status"
    get_status_badge.admin_order_field = "is_active"
    
    def get_shipments_info(self, obj):
        """Display shipment statistics."""
        total = getattr(obj, 'total_shipments', 0)
        active = getattr(obj, 'active_shipments', 0)
        
        if total == 0:
            return format_html('<span style="color: #94a3b8; font-size: 11px;">No shipments</span>')
        
        return format_html(
            '<span style="background: rgba(14,165,233,0.1); color: #0ea5e9; padding: 4px 10px; '
            'border-radius: 12px; font-weight: 600; font-size: 11px;">📦 {} total | 🚚 {} active</span>',
            total,
            active
        )
    
    get_shipments_info.short_description = "📦 Shipments"
    get_shipments_info.admin_order_field = "total_shipments"
    
    def get_actions(self, obj):
        """Quick action links."""
        actions = []
        
        # Edit link
        edit_url = reverse('admin:shipments_driver_change', args=[obj.pk])
        actions.append(
            format_html(
                '<a href="{}" style="color: #0ea5e9; font-size: 16px; '
                'text-decoration: none; margin-right: 8px;" title="Edit">✏️</a>',
                edit_url
            )
        )
        
        # View shipments
        shipments_url = reverse('admin:shipments_shipment_changelist') + f'?driver__id__exact={obj.id}'
        actions.append(
            format_html(
                '<a href="{}" style="color: #10b981; font-size: 16px; '
                'text-decoration: none; margin-right: 8px;" title="View Shipments">📦</a>',
                shipments_url
            )
        )
        
        return mark_safe(" ".join(actions))
    
    get_actions.short_description = "⚡ Actions"
    
    actions = ["toggle_active_status", "make_available", "make_busy"]
    
    def toggle_active_status(self, request, queryset):
        """Toggle driver availability status."""
        for driver in queryset:
            driver.is_active = not driver.is_active
            driver.save()
        self.message_user(request, f"✅ Toggled status for {queryset.count()} driver(s).")
    
    toggle_active_status.short_description = "🔄 Toggle availability status"
    
    def make_available(self, request, queryset):
        """Mark drivers as available."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"✅ Marked {count} driver(s) as Available.")
    
    make_available.short_description = "✅ Mark as Available"
    
    def make_busy(self, request, queryset):
        """Mark drivers as busy."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"⏸ Marked {count} driver(s) as Busy.")
    
    make_busy.short_description = "⏸ Mark as Busy"


# ============================================================================
# WAREHOUSE MANAGER ADMIN
# ============================================================================

class WarehouseManagerAdminForm(forms.ModelForm):
    """Enhanced form with role conflict validation."""
    
    class Meta:
        model = WarehouseManager
        fields = ["user"]
    
    def clean_user(self):
        """Prevent driver/manager role conflicts."""
        u = self.cleaned_data.get("user")
        if not u:
            return u
        
        if Driver.objects.filter(user=u).exists():
            raise forms.ValidationError(
                f"⚠ User '{u.username}' is already a Driver. "
                "A user cannot have both roles simultaneously."
            )
        return u


@admin.register(WarehouseManager)
class WarehouseManagerAdmin(admin.ModelAdmin):
    """
    Warehouse Manager profile administration.
    """
    
    form = WarehouseManagerAdminForm
    autocomplete_fields = ["user"]
    
    list_display = ("id", "get_manager_name", "get_manager_phone", "get_role_badge", "get_actions")
    list_display_links = ("id", "get_manager_name")
    search_fields = ("user__username", "user__phone", "user__first_name", "user__last_name")
    list_per_page = 25
    
    fieldsets = (
        ("👤 Manager Information", {
            "fields": ("user",),
            "description": "Select the user account for this warehouse manager profile.",
        }),
    )
    
    def get_manager_name(self, obj):
        """Display manager name with icon."""
        return format_html('<strong>📦 {}</strong>', obj.user.username)
    
    get_manager_name.short_description = "Manager Name"
    get_manager_name.admin_order_field = "user__username"
    
    def get_manager_phone(self, obj):
        """Display formatted phone."""
        return format_html('<span style="color: #64748b;">📞 {}</span>', obj.user.phone)
    
    get_manager_phone.short_description = "Phone"
    get_manager_phone.admin_order_field = "user__phone"
    
    def get_role_badge(self, obj):
        """Display role badge."""
        return format_html(
            '<span style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); '
            'color: white; padding: 6px 14px; border-radius: 20px; font-size: 11px; '
            'font-weight: 600; box-shadow: 0 2px 10px rgba(59,130,246,0.3);">📦 Warehouse Manager</span>'
        )
    
    get_role_badge.short_description = "Role"
    
    def get_actions(self, obj):
        """Quick action links."""
        edit_url = reverse('admin:shipments_warehousemanager_change', args=[obj.pk])
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-size: 16px; '
            'text-decoration: none;" title="Edit">✏️</a>',
            edit_url
        )
    
    get_actions.short_description = "⚡ Actions"


# ============================================================================
# PRODUCT ADMIN
# ============================================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Product inventory management with stock tracking.
    """
    
    list_display = (
        "id",
        "get_product_name",
        "get_price_display",
        "get_stock_badge",
        "unit",
        "get_status_badge",
        "get_image_preview",
        "created_at",
        "get_actions",
    )
    
    list_display_links = ("id", "get_product_name")
    list_filter = ("is_active", "unit", "created_at")
    search_fields = ("name", "unit")
    ordering = ("-created_at",)
    list_per_page = 25
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("📦 Product Information", {
            "fields": ("name", "unit"),
        }),
        ("💰 Pricing & Stock", {
            "fields": ("price", "stock_qty"),
            "description": "Set product price and available stock quantity.",
        }),
        ("🖼 Product Image", {
            "fields": ("image",),
            "classes": ("collapse",),
        }),
        ("📊 Status", {
            "fields": ("is_active",),
        }),
    )
    
    readonly_fields = ("created_at",)
    
    def get_queryset(self, request):
        """Optimize with shipment counting."""
        qs = super().get_queryset(request)
        qs = qs.annotate(shipments_count=Count('shipments'))
        return qs
    
    def get_product_name(self, obj):
        """Display product name with icon."""
        return format_html('<strong>📦 {}</strong>', obj.name)
    
    get_product_name.short_description = "Product Name"
    get_product_name.admin_order_field = "name"
    
    def get_price_display(self, obj):
        """Formatted price display."""
        return format_html(
            '<span style="color: #10b981; font-weight: 600;">💰 {:.2f} SAR</span>',
            obj.price
        )
    
    get_price_display.short_description = "Price"
    get_price_display.admin_order_field = "price"
    
    def get_stock_badge(self, obj):
        """Stock level indicator with color coding."""
        if obj.stock_qty == 0:
            color = "#ef4444"
            text = "Out of Stock"
            icon = "❌"
        elif obj.stock_qty < 10:
            color = "#f59e0b"
            text = f"Low Stock ({obj.stock_qty})"
            icon = "⚠"
        else:
            color = "#10b981"
            text = f"In Stock ({obj.stock_qty})"
            icon = "✓"
        
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 12px; '
            'border-radius: 16px; font-size: 11px; font-weight: 600; '
            'box-shadow: 0 2px 8px rgba(0,0,0,0.15);">{} {}</span>',
            color, icon, text
        )
    
    get_stock_badge.short_description = "📊 Stock Status"
    get_stock_badge.admin_order_field = "stock_qty"
    
    def get_status_badge(self, obj):
        """Active/Inactive status."""
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981; font-weight: 600;">● Active</span>'
            )
        return format_html(
            '<span style="color: #ef4444; font-weight: 600;">● Inactive</span>'
        )
    
    get_status_badge.short_description = "Status"
    get_status_badge.admin_order_field = "is_active"
    
    def get_image_preview(self, obj):
        """Small image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; object-fit: cover; '
                'border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        return format_html('<span style="color: #94a3b8; font-size: 11px;">No image</span>')
    
    get_image_preview.short_description = "🖼 Image"
    
    def get_actions(self, obj):
        """Quick actions."""
        edit_url = reverse('admin:shipments_product_change', args=[obj.pk])
        shipments_url = reverse('admin:shipments_shipment_changelist') + f'?product__id__exact={obj.id}'
        
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-size: 16px; text-decoration: none; '
            'margin-right: 8px;" title="Edit">✏️</a>'
            '<a href="{}" style="color: #10b981; font-size: 16px; text-decoration: none;" '
            'title="View Shipments">📦</a>',
            edit_url, shipments_url
        )
    
    get_actions.short_description = "⚡ Actions"
    
    actions = ["activate_products", "deactivate_products", "restock_low_items"]
    
    def activate_products(self, request, queryset):
        """Activate selected products."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"✅ Activated {count} product(s).")
    
    activate_products.short_description = "✅ Activate selected products"
    
    def deactivate_products(self, request, queryset):
        """Deactivate selected products."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"⏸ Deactivated {count} product(s).")
    
    deactivate_products.short_description = "⏸ Deactivate selected products"
    
    def restock_low_items(self, request, queryset):
        """Mark low stock items for restock."""
        low_stock = queryset.filter(stock_qty__lt=10)
        self.message_user(
            request,
            f"⚠ Found {low_stock.count()} item(s) with low stock. Please restock soon!",
            level='WARNING'
        )
    
    restock_low_items.short_description = "⚠ Identify low stock items"


# ============================================================================
# WAREHOUSE ADMIN
# ============================================================================

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    """Warehouse location management."""
    
    list_display = ("get_warehouse_name", "location", "get_shipment_count", "created_at", "get_actions")
    list_display_links = ("get_warehouse_name",)
    list_filter = ("location", "created_at")
    search_fields = ("name", "location")
    date_hierarchy = "created_at"
    list_per_page = 25
    
    fieldsets = (
        ("🏢 Warehouse Information", {
            "fields": ("name", "location"),
            "description": "Enter warehouse name and location details.",
        }),
    )
    
    def get_queryset(self, request):
        """Add shipment counting."""
        qs = super().get_queryset(request)
        qs = qs.annotate(shipment_count=Count('shipment'))
        return qs
    
    def get_warehouse_name(self, obj):
        """Display warehouse name."""
        return format_html('<strong>🏢 {}</strong>', obj.name)
    
    get_warehouse_name.short_description = "Warehouse"
    get_warehouse_name.admin_order_field = "name"
    
    def get_shipment_count(self, obj):
        """Display shipment count."""
        count = getattr(obj, 'shipment_count', 0)
        if count > 0:
            return format_html(
                '<span style="background: rgba(14,165,233,0.1); color: #0ea5e9; '
                'padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;">'
                '📦 {} shipment{}</span>',
                count, 's' if count != 1 else ''
            )
        return format_html('<span style="color: #94a3b8; font-size: 11px;">No shipments</span>')
    
    get_shipment_count.short_description = "📦 Shipments"
    get_shipment_count.admin_order_field = "shipment_count"
    
    def get_actions(self, obj):
        """Quick actions."""
        edit_url = reverse('admin:shipments_warehouse_change', args=[obj.pk])
        shipments_url = reverse('admin:shipments_shipment_changelist') + f'?warehouse__id__exact={obj.id}'
        
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-size: 16px; text-decoration: none; '
            'margin-right: 8px;" title="Edit">✏️</a>'
            '<a href="{}" style="color: #10b981; font-size: 16px; text-decoration: none;" '
            'title="View Shipments">📦</a>',
            edit_url, shipments_url
        )
    
    get_actions.short_description = "⚡ Actions"


# ============================================================================
# CUSTOMER ADMIN
# ============================================================================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Customer management with enhanced address handling."""
    
    list_display = (
        "get_customer_name",
        "get_phone_display",
        "get_address_count",
        "get_shipment_count",
        "get_actions",
    )
    
    list_display_links = ("get_customer_name",)
    search_fields = ("name", "phone", "address", "address2", "address3")
    list_per_page = 50
    
    fieldsets = (
        ("👤 Customer Information", {
            "fields": ("name", "phone"),
        }),
        ("📍 Addresses", {
            "fields": ("address", "address2", "address3"),
            "description": "Enter up to 3 delivery addresses for this customer.",
        }),
    )
    
    def get_queryset(self, request):
        """Add shipment counting."""
        qs = super().get_queryset(request)
        qs = qs.annotate(shipment_count=Count('shipment'))
        return qs
    
    def get_customer_name(self, obj):
        """Display customer name."""
        return format_html('<strong>👤 {}</strong>', obj.name)
    
    get_customer_name.short_description = "Customer Name"
    get_customer_name.admin_order_field = "name"
    
    def get_phone_display(self, obj):
        """Display phone."""
        return format_html('<span style="color: #64748b;">📞 {}</span>', obj.phone)
    
    get_phone_display.short_description = "Phone"
    get_phone_display.admin_order_field = "phone"
    
    def get_address_count(self, obj):
        """Count of saved addresses."""
        count = sum([
            1 for addr in [obj.address, obj.address2, obj.address3]
            if addr and addr.strip()
        ])
        
        if count == 0:
            return format_html('<span style="color: #ef4444;">⚠ No addresses</span>')
        
        return format_html(
            '<span style="color: #10b981;">📍 {} address{}</span>',
            count, 'es' if count != 1 else ''
        )
    
    get_address_count.short_description = "📍 Addresses"
    
    def get_shipment_count(self, obj):
        """Display shipment count."""
        count = getattr(obj, 'shipment_count', 0)
        if count > 0:
            return format_html(
                '<span style="background: rgba(14,165,233,0.1); color: #0ea5e9; '
                'padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;">'
                '📦 {}</span>',
                count
            )
        return format_html('<span style="color: #94a3b8; font-size: 11px;">—</span>')
    
    get_shipment_count.short_description = "📦 Shipments"
    get_shipment_count.admin_order_field = "shipment_count"
    
    def get_actions(self, obj):
        """Quick actions."""
        edit_url = reverse('admin:shipments_customer_change', args=[obj.pk])
        shipments_url = reverse('admin:shipments_shipment_changelist') + f'?customer__id__exact={obj.id}'
        
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-size: 16px; text-decoration: none; '
            'margin-right: 8px;" title="Edit">✏️</a>'
            '<a href="{}" style="color: #10b981; font-size: 16px; text-decoration: none;" '
            'title="View Shipments">📦</a>',
            edit_url, shipments_url
        )
    
    get_actions.short_description = "⚡ Actions"


# ============================================================================
# SHIPMENT ADMIN
# ============================================================================

class ShipmentAdminForm(forms.ModelForm):
    """Enhanced shipment form with smart address selection."""
    
    customer_address = forms.ChoiceField(
        required=False,
        choices=[("", "— Choose customer first —")],
        label="Customer Address",
    )
    
    class Meta:
        model = Shipment
        fields = "__all__"
    
    def _get_customer(self):
        """Helper to get customer from various sources."""
        if self.instance and self.instance.pk and self.instance.customer_id:
            return self.instance.customer
        
        cid = self.initial.get("customer") or self.data.get("customer")
        if cid:
            try:
                return Customer.objects.get(pk=cid)
            except (Customer.DoesNotExist, ValueError):
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
            self.fields["customer_address"].choices = [("", "— Select address —")] + [
                (a, a) for a in addresses
            ]
            if len(addresses) == 1:
                self.fields["customer_address"].initial = addresses[0]
        else:
            self.fields["customer_address"].choices = [("", "— No addresses available —")]
            self.fields["customer_address"].help_text = "Please add addresses to the customer profile first."
    
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
            self.add_error("customer", "⚠ The selected customer has no saved addresses.")
            self.add_error("customer_address", "Cannot create shipment without a delivery address.")
            return cleaned
        
        if len(allowed) == 1 and not addr:
            cleaned["customer_address"] = allowed[0]
            return cleaned
        
        if not addr:
            self.add_error("customer_address", "⚠ Please select a delivery address.")
            return cleaned
        
        if addr not in allowed:
            self.add_error("customer_address", "⚠ Selected address is not valid for this customer.")
            return cleaned
        
        cleaned["customer_address"] = addr
        return cleaned


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    """
    Comprehensive shipment management with tracking and status updates.
    
    Features:
    - Visual status indicators
    - Driver assignment tracking
    - Stock management integration
    - Address validation
    - Status timeline
    """
    
    form = ShipmentAdminForm
    autocomplete_fields = ("product", "warehouse", "driver", "customer")
    
    list_display = (
        "id",
        "get_product_name",
        "get_customer_info",
        "get_driver_info",
        "get_warehouse_name",
        "get_status_badge",
        "get_created_date",
        "get_actions",
    )
    
    list_display_links = ("id",)
    list_filter = ("warehouse", "current_status", "created_at")
    search_fields = (
        "id",
        "product__name",
        "customer__name",
        "customer__phone",
        "driver__user__username",
        "customer_address",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    
    fieldsets = (
        ("📦 Shipment Details", {
            "fields": ("product", "warehouse"),
        }),
        ("👤 Customer Information", {
            "fields": ("customer", "customer_address"),
            "description": "Select customer and delivery address. Address must be pre-configured in customer profile.",
        }),
        ("🚗 Driver Assignment", {
            "fields": ("driver",),
            "classes": ("collapse",),
            "description": "Assign a driver to this shipment. Leave empty to assign later.",
        }),
        ("📝 Additional Information", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("📊 Status & Tracking", {
            "fields": ("current_status", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ("created_at", "updated_at", "current_status")
    
    def get_queryset(self, request):
        """Optimize with related fields."""
        qs = super().get_queryset(request)
        qs = qs.select_related(
            "product",
            "warehouse",
            "driver__user",
            "customer"
        ).prefetch_related("status_updates")
        return qs
    
    def get_product_name(self, obj):
        """Display product name."""
        return format_html('<strong>📦 {}</strong>', obj.product.name)
    
    get_product_name.short_description = "Product"
    get_product_name.admin_order_field = "product__name"
    
    def get_customer_info(self, obj):
        """Display customer name and truncated address."""
        address = obj.customer_address[:30] + "..." if len(obj.customer_address) > 30 else obj.customer_address
        return format_html(
            '<div><strong>{}</strong></div>'
            '<div style="color: #64748b; font-size: 11px;">📍 {}</div>',
            obj.customer.name,
            address
        )
    
    get_customer_info.short_description = "Customer & Address"
    get_customer_info.admin_order_field = "customer__name"
    
    def get_driver_info(self, obj):
        """Display driver information."""
        if obj.driver:
            status_icon = "✓" if obj.driver.is_active else "⏸"
            status_color = "#10b981" if obj.driver.is_active else "#ef4444"
            return format_html(
                '<span style="color: {};">{} 🚗 {}</span>',
                status_color,
                status_icon,
                obj.driver.user.username
            )
        return format_html('<span style="color: #94a3b8; font-style: italic;">Not assigned</span>')
    
    get_driver_info.short_description = "Driver"
    get_driver_info.admin_order_field = "driver__user__username"
    
    def get_warehouse_name(self, obj):
        """Display warehouse."""
        return format_html('<span style="color: #64748b;">🏢 {}</span>', obj.warehouse.name)
    
    get_warehouse_name.short_description = "Warehouse"
    get_warehouse_name.admin_order_field = "warehouse__name"
    
    def get_status_badge(self, obj):
        """Enhanced status badge with color coding."""
        status_styles = {
            'PENDING': ('⏳', '#f59e0b', 'Pending'),
            'ASSIGNED': ('📋', '#3b82f6', 'Assigned'),
            'IN_TRANSIT': ('🚚', '#0ea5e9', 'In Transit'),
            'DELIVERED': ('✅', '#10b981', 'Delivered'),
            'CANCELLED': ('❌', '#ef4444', 'Cancelled'),
        }
        
        icon, color, text = status_styles.get(obj.current_status, ('❓', '#94a3b8', obj.current_status))
        
        return format_html(
            '<span style="background: {}; color: white; padding: 6px 14px; '
            'border-radius: 20px; font-size: 11px; font-weight: 600; '
            'box-shadow: 0 2px 10px rgba(0,0,0,0.15);">{} {}</span>',
            color, icon, text
        )
    
    get_status_badge.short_description = "Status"
    get_status_badge.admin_order_field = "current_status"
    
    def get_created_date(self, obj):
        """Display formatted creation date."""
        return format_html(
            '<span style="color: #64748b; font-size: 11px;">📅 {}</span>',
            obj.created_at.strftime("%Y-%m-%d %H:%M")
        )
    
    get_created_date.short_description = "Created"
    get_created_date.admin_order_field = "created_at"
    
    def get_actions(self, obj):
        """Quick action links."""
        edit_url = reverse('admin:shipments_shipment_change', args=[obj.pk])
        status_url = reverse('admin:shipments_statusupdate_changelist') + f'?shipment__id__exact={obj.id}'
        
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-size: 16px; text-decoration: none; '
            'margin-right: 8px;" title="Edit">✏️</a>'
            '<a href="{}" style="color: #10b981; font-size: 16px; text-decoration: none;" '
            'title="View Status Updates">📊</a>',
            edit_url, status_url
        )
    
    get_actions.short_description = "⚡ Actions"
    
    actions = ["assign_to_driver", "mark_as_delivered", "cancel_shipments"]
    
    def assign_to_driver(self, request, queryset):
        """Bulk assign shipments to drivers."""
        unassigned = queryset.filter(driver__isnull=True)
        self.message_user(
            request,
            f"📋 {unassigned.count()} unassigned shipment(s) ready for driver assignment. "
            "Please assign individually for proper stock management.",
            level='INFO'
        )
    
    assign_to_driver.short_description = "📋 Check unassigned shipments"
    
    def mark_as_delivered(self, request, queryset):
        """Mark shipments as delivered."""
        eligible = queryset.filter(current_status__in=['IN_TRANSIT', 'ASSIGNED'])
        count = eligible.update(current_status='DELIVERED')
        self.message_user(request, f"✅ Marked {count} shipment(s) as Delivered.")
    
    mark_as_delivered.short_description = "✅ Mark as Delivered"
    
    def cancel_shipments(self, request, queryset):
        """Cancel selected shipments."""
        eligible = queryset.exclude(current_status__in=['DELIVERED', 'CANCELLED'])
        count = eligible.update(current_status='CANCELLED')
        self.message_user(request, f"❌ Cancelled {count} shipment(s).")
    
    cancel_shipments.short_description = "❌ Cancel selected shipments"
    
    def get_changeform_initial_data(self, request):
        """Pre-fill customer from GET parameter."""
        initial = super().get_changeform_initial_data(request)
        cid = request.GET.get("customer")
        if cid:
            initial["customer"] = cid
        return initial


# ============================================================================
# STATUS UPDATE ADMIN
# ============================================================================

@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    """
    Status update tracking with timeline view.
    """
    
    autocomplete_fields = ["shipment"]
    
    list_display = (
        "get_shipment_id",
        "get_status_badge",
        "get_timestamp",
        "get_location_info",
        "get_actions",
    )
    
    list_display_links = ("get_shipment_id",)
    list_filter = ("status", "timestamp")
    search_fields = ("shipment__id", "shipment__driver__user__username", "notes")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    list_per_page = 50
    
    fieldsets = (
        ("📦 Shipment & Status", {
            "fields": ("shipment", "status"),
        }),
        ("📍 Location Data", {
            "fields": ("latitude", "longitude", "location_accuracy_m"),
            "classes": ("collapse",),
            "description": "GPS coordinates and accuracy (optional).",
        }),
        ("📝 Notes", {
            "fields": ("notes",),
            "classes": ("collapse",),
        }),
        ("⏱ Timestamp", {
            "fields": ("timestamp",),
        }),
    )
    
    readonly_fields = ("timestamp",)
    
    def get_shipment_id(self, obj):
        """Display shipment ID with link."""
        url = reverse('admin:shipments_shipment_change', args=[obj.shipment.id])
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-weight: 600;">#{}</a>',
            url, obj.shipment.id
        )
    
    get_shipment_id.short_description = "Shipment"
    get_shipment_id.admin_order_field = "shipment__id"
    
    def get_status_badge(self, obj):
        """Status badge."""
        status_styles = {
            'PENDING': ('⏳', '#f59e0b'),
            'ASSIGNED': ('📋', '#3b82f6'),
            'IN_TRANSIT': ('🚚', '#0ea5e9'),
            'DELIVERED': ('✅', '#10b981'),
            'CANCELLED': ('❌', '#ef4444'),
        }
        
        icon, color = status_styles.get(obj.status, ('❓', '#94a3b8'))
        
        return format_html(
            '<span style="background: {}; color: white; padding: 6px 14px; '
            'border-radius: 20px; font-size: 11px; font-weight: 600;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    
    get_status_badge.short_description = "Status"
    get_status_badge.admin_order_field = "status"
    
    def get_timestamp(self, obj):
        """Formatted timestamp."""
        return format_html(
            '<span style="color: #64748b; font-size: 11px;">⏱ {}</span>',
            obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    get_timestamp.short_description = "Time"
    get_timestamp.admin_order_field = "timestamp"
    
    def get_location_info(self, obj):
        """Display GPS info if available."""
        if obj.latitude and obj.longitude:
            maps_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank" style="color: #10b981; text-decoration: none;">'
                '📍 GPS ({:.4f}, {:.4f})</a>',
                maps_url, obj.latitude, obj.longitude
            )
        return format_html('<span style="color: #94a3b8; font-size: 11px;">No GPS data</span>')
    
    get_location_info.short_description = "Location"
    
    def get_actions(self, obj):
        """Quick actions."""
        edit_url = reverse('admin:shipments_statusupdate_change', args=[obj.pk])
        shipment_url = reverse('admin:shipments_shipment_change', args=[obj.shipment.id])
        
        return format_html(
            '<a href="{}" style="color: #0ea5e9; font-size: 16px; text-decoration: none; '
            'margin-right: 8px;" title="Edit">✏️</a>'
            '<a href="{}" style="color: #10b981; font-size: 16px; text-decoration: none;" '
            'title="View Shipment">📦</a>',
            edit_url, shipment_url
        )
    
    get_actions.short_description = "⚡ Actions"
