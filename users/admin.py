from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .models import CustomUser
from shipments.models import Driver, WarehouseManager


class DriverInline(admin.StackedInline):
    """
    Inline form to manage Driver profile with enhanced UX.
    Shows driver-specific settings in a clean collapsible panel.
    """
    model = Driver
    can_delete = True
    verbose_name = "🚗 Driver Profile"
    verbose_name_plural = "🚗 Driver Profiles"
    fk_name = "user"
    fields = ("is_active",)
    extra = 0
    max_num = 1
    classes = ('collapse',)
    
    def get_extra(self, request, obj=None, **kwargs):
        """Don't show extra empty forms."""
        return 0


class WarehouseManagerInline(admin.StackedInline):
    """
    Inline form to manage Warehouse Manager profile.
    Allows quick assignment of manager role.
    """
    model = WarehouseManager
    can_delete = True
    verbose_name = "📦 Warehouse Manager Profile"
    verbose_name_plural = "📦 Warehouse Manager Profiles"
    fk_name = "user"
    fields = ()
    extra = 0
    max_num = 1
    classes = ('collapse',)
    
    def get_extra(self, request, obj=None, **kwargs):
        """Don't show extra empty forms."""
        return 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Enhanced User administration with comprehensive role management.
    
    Features:
    - Visual role indicators with color-coded badges
    - Bulk role assignment/removal actions
    - Inline role management for individual users
    - Advanced search and filtering
    - Quick stats display
    """
    
    # Inline forms for role management
    inlines = [DriverInline, WarehouseManagerInline]
    
    # Field organization for editing existing users
    fieldsets = (
        ("👤 Account Information", {
            "fields": ("username", "password"),
            "description": "Basic account credentials. Use 'Change password form' link below to update password.",
        }),
        ("📋 Personal Information", {
            "fields": ("first_name", "last_name", "email"),
            "classes": ("collapse",),
        }),
        ("📞 Contact Information", {
            "fields": ("phone",),
            "description": "Saudi phone number in format: +966XXXXXXXXX",
        }),
        ("🔐 Permissions & Access", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            "classes": ("collapse",),
            "description": "Control user access levels and permissions. Staff can access admin. Superuser has all permissions.",
        }),
        ("📅 Important Dates", {
            "fields": ("last_login", "date_joined"),
            "classes": ("collapse",),
        }),
    )
    
    # Field organization for creating new users
    add_fieldsets = (
        ("👤 Create New User", {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2"),
            "description": "Enter username and a strong password (min 8 characters, mix of letters/numbers/symbols).",
        }),
        ("📞 Contact Information", {
            "fields": ("phone",),
            "description": "Required. Saudi phone number format: +966XXXXXXXXX (must be unique).",
        }),
        ("🔐 Basic Permissions", {
            "fields": ("is_staff", "is_active"),
            "description": "✅ Active: User can log in | ✅ Staff: User can access admin panel",
        }),
    )
    
    # Enhanced list display
    list_display = (
        "username",
        "phone",
        "get_user_roles",
        "get_user_status",
        "is_staff",
        "get_shipments_count",
        "date_joined",
        "get_actions",
    )
    
    list_display_links = ("username",)
    list_filter = ("is_staff", "is_active", "is_superuser", "date_joined", "last_login")
    search_fields = ("username", "phone", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    list_per_page = 25
    date_hierarchy = "date_joined"
    
    # Actions for bulk operations
    actions = [
        "make_driver",
        "make_warehouse_manager",
        "remove_driver_role",
        "remove_manager_role",
        "activate_users",
        "deactivate_users",
    ]
    
    def get_queryset(self, request):
        """
        Optimize queries with prefetch_related and annotations.
        """
        qs = super().get_queryset(request)
        qs = qs.select_related(
            'driver_profile',
            'warehouse_manager_profile',
        ).annotate(
            driver_shipments_count=Count(
                'driver_profile__shipment',
                filter=Q(driver_profile__isnull=False)
            )
        )
        return qs
    
    def get_user_roles(self, obj):
        """
        Display user roles with beautiful colored badges.
        """
        roles = []
        
        if hasattr(obj, "driver_profile"):
            driver = obj.driver_profile
            status_color = "#10b981" if driver.is_active else "#ef4444"
            status_text = "Available" if driver.is_active else "Busy"
            status_icon = "✓" if driver.is_active else "⏸"
            roles.append(
                format_html(
                    '<span style="background: {}; color: white; padding: 6px 12px; '
                    'border-radius: 16px; font-size: 11px; font-weight: 600; '
                    'margin-right: 6px; display: inline-block; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">'
                    '{} 🚗 Driver - {}</span>',
                    status_color,
                    status_icon,
                    status_text
                )
            )
        
        if hasattr(obj, "warehouse_manager_profile"):
            roles.append(
                format_html(
                    '<span style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); '
                    'color: white; padding: 6px 12px; border-radius: 16px; font-size: 11px; '
                    'font-weight: 600; display: inline-block; box-shadow: 0 2px 8px rgba(59,130,246,0.3);">'
                    '📦 Warehouse Manager</span>'
                )
            )
        
        if not roles:
            return format_html(
                '<span style="color: #94a3b8; font-style: italic; font-size: 11px;">'
                '⚠ No role assigned</span>'
            )
        
        return mark_safe(" ".join(roles))
    
    get_user_roles.short_description = "🎭 Roles & Status"
    get_user_roles.admin_order_field = "driver_profile__is_active"
    
    def get_user_status(self, obj):
        """Display user active status with visual indicator."""
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981; font-weight: 600;">● Active</span>'
            )
        return format_html(
            '<span style="color: #ef4444; font-weight: 600;">● Inactive</span>'
        )
    
    get_user_status.short_description = "Status"
    get_user_status.admin_order_field = "is_active"
    
    def get_shipments_count(self, obj):
        """Display shipments count for drivers."""
        if hasattr(obj, "driver_profile"):
            count = getattr(obj, 'driver_shipments_count', 0)
            if count > 0:
                return format_html(
                    '<span style="background: rgba(14, 165, 233, 0.1); color: #0ea5e9; '
                    'padding: 4px 10px; border-radius: 12px; font-weight: 600; font-size: 11px;">'
                    '📦 {} shipment{}</span>',
                    count,
                    's' if count != 1 else ''
                )
            return format_html('<span style="color: #94a3b8; font-size: 11px;">No shipments</span>')
        return format_html('<span style="color: #94a3b8; font-size: 11px;">—</span>')
    
    get_shipments_count.short_description = "📦 Shipments"
    get_shipments_count.admin_order_field = "driver_shipments_count"
    
    def get_actions(self, obj):
        """Quick action buttons for each user."""
        actions = []
        
        # View button
        view_url = reverse('admin:users_customuser_change', args=[obj.pk])
        actions.append(
            format_html(
                '<a href="{}" style="color: #0ea5e9; text-decoration: none; '
                'font-size: 16px; margin-right: 8px;" title="Edit User">✏️</a>',
                view_url
            )
        )
        
        # Driver shipments link
        if hasattr(obj, "driver_profile"):
            shipments_url = reverse('admin:shipments_shipment_changelist') + f'?driver__id__exact={obj.driver_profile.id}'
            actions.append(
                format_html(
                    '<a href="{}" style="color: #10b981; text-decoration: none; '
                    'font-size: 16px; margin-right: 8px;" title="View Shipments">📦</a>',
                    shipments_url
                )
            )
        
        return mark_safe(" ".join(actions))
    
    get_actions.short_description = "⚡ Actions"
    
    # Bulk Actions
    
    def make_driver(self, request, queryset):
        """Assign Driver role to selected users."""
        count = 0
        skipped = []
        
        for user in queryset:
            if hasattr(user, "driver_profile") or hasattr(user, "warehouse_manager_profile"):
                skipped.append(user.username)
                continue
            Driver.objects.get_or_create(user=user, defaults={"is_active": True})
            count += 1
        
        message = f"✅ Successfully assigned Driver role to {count} user(s)."
        if skipped:
            message += f" ⚠ Skipped {len(skipped)} user(s) (already have roles): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."
        
        self.message_user(request, message)
    
    make_driver.short_description = "🚗 Assign Driver role to selected users"
    
    def make_warehouse_manager(self, request, queryset):
        """Assign Warehouse Manager role to selected users."""
        count = 0
        skipped = []
        
        for user in queryset:
            if hasattr(user, "driver_profile") or hasattr(user, "warehouse_manager_profile"):
                skipped.append(user.username)
                continue
            WarehouseManager.objects.get_or_create(user=user)
            count += 1
        
        message = f"✅ Successfully assigned Warehouse Manager role to {count} user(s)."
        if skipped:
            message += f" ⚠ Skipped {len(skipped)} user(s) (already have roles): {', '.join(skipped[:5])}"
            if len(skipped) > 5:
                message += f" and {len(skipped) - 5} more..."
        
        self.message_user(request, message)
    
    make_warehouse_manager.short_description = "📦 Assign Warehouse Manager role to selected users"
    
    def remove_driver_role(self, request, queryset):
        """Remove Driver role from selected users."""
        count = 0
        for user in queryset:
            if hasattr(user, "driver_profile"):
                user.driver_profile.delete()
                count += 1
        
        self.message_user(request, f"✅ Successfully removed Driver role from {count} user(s).")
    
    remove_driver_role.short_description = "❌ Remove Driver role from selected users"
    
    def remove_manager_role(self, request, queryset):
        """Remove Warehouse Manager role from selected users."""
        count = 0
        for user in queryset:
            if hasattr(user, "warehouse_manager_profile"):
                user.warehouse_manager_profile.delete()
                count += 1
        
        self.message_user(request, f"✅ Successfully removed Warehouse Manager role from {count} user(s).")
    
    remove_manager_role.short_description = "❌ Remove Warehouse Manager role from selected users"
    
    def activate_users(self, request, queryset):
        """Activate selected users."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"✅ Activated {count} user(s).")
    
    activate_users.short_description = "✅ Activate selected users"
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users."""
        count = queryset.update(is_active=False)
        self.message_user(request, f"⏸ Deactivated {count} user(s).")
    
    deactivate_users.short_description = "⏸ Deactivate selected users"
    
    def get_inline_instances(self, request, obj=None):
        """Only show inline forms when editing existing users."""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Enhanced save with automatic logging."""
        super().save_model(request, obj, form, change)
        
        if not change:
            self.message_user(
                request,
                f"✅ User '{obj.username}' created successfully. You can now assign a role below.",
                level='SUCCESS'
            )
