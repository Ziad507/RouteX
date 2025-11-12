from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CustomUser
from shipments.models import Driver, WarehouseManager


class DriverInline(admin.StackedInline):
    """
    Inline form to manage Driver profile directly from User admin page.
    Allows creating/editing driver status without navigating to separate page.
    """
    model = Driver
    can_delete = True
    verbose_name = "Driver Profile"
    verbose_name_plural = "Driver Profile"
    fk_name = "user"
    fields = ("is_active",)
    extra = 0
    max_num = 1


class WarehouseManagerInline(admin.StackedInline):
    """
    Inline form to manage WarehouseManager profile directly from User admin page.
    Allows assigning warehouse manager role without navigating to separate page.
    """
    model = WarehouseManager
    can_delete = True
    verbose_name = "Warehouse Manager Profile"
    verbose_name_plural = "Warehouse Manager Profile"
    fk_name = "user"
    fields = ()  # No additional fields, just the relationship
    extra = 0
    max_num = 1


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Enhanced User admin with role management (Driver/WarehouseManager) via inline forms.
    Supports creating, editing, and deleting users with automatic role assignment.
    """
    # Inline forms for role management
    inlines = [DriverInline, WarehouseManagerInline]
    
    # Field organization
    fieldsets = UserAdmin.fieldsets + (
        ("Contact Information", {"fields": ("phone",)}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("username", "password1", "password2")}),
        ("Contact Information", {"fields": ("phone",)}),
        ("Permissions", {"fields": ("is_staff", "is_active")}),
    )
    
    # List display with role indicators
    list_display = (
        "username",
        "phone",
        "get_user_roles",
        "is_staff",
        "is_active",
        "date_joined",
    )
    
    list_filter = ("is_staff", "is_active", "date_joined")
    search_fields = ("username", "phone", "email")
    ordering = ("-date_joined",)
    
    # Actions for bulk role management
    actions = ["make_driver", "make_warehouse_manager", "remove_driver_role", "remove_manager_role"]
    
    def get_user_roles(self, obj):
        """
        Display user roles (Driver/Warehouse Manager) as colored badges.
        """
        roles = []
        
        # Check if user is a driver
        if hasattr(obj, "driver_profile"):
            driver = obj.driver_profile
            status_color = "#10b981" if driver.is_active else "#ef4444"
            status_text = "Available" if driver.is_active else "Busy"
            roles.append(
                format_html(
                    '<span style="background: {}; color: white; padding: 4px 10px; '
                    'border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 4px;">'
                    '🚗 Driver ({})</span>',
                    status_color,
                    status_text
                )
            )
        
        # Check if user is a warehouse manager
        if hasattr(obj, "warehouse_manager_profile"):
            roles.append(
                format_html(
                    '<span style="background: #3b82f6; color: white; padding: 4px 10px; '
                    'border-radius: 12px; font-size: 11px; font-weight: 600;">'
                    '📦 Warehouse Manager</span>'
                )
            )
        
        if not roles:
            return format_html(
                '<span style="color: #94a3b8; font-style: italic;">No role assigned</span>'
            )
        
        return mark_safe(" ".join(roles))
    
    get_user_roles.short_description = "Roles"
    get_user_roles.allow_tags = True
    
    def make_driver(self, request, queryset):
        """
        Bulk action: Assign Driver role to selected users.
        Skips users who already have Driver or WarehouseManager profiles.
        """
        count = 0
        skipped = []
        
        for user in queryset:
            # Skip if already has a role
            if hasattr(user, "driver_profile") or hasattr(user, "warehouse_manager_profile"):
                skipped.append(user.username)
                continue
            
            Driver.objects.get_or_create(user=user, defaults={"is_active": True})
            count += 1
        
        message = f"Successfully assigned Driver role to {count} user(s)."
        if skipped:
            message += f" Skipped {len(skipped)} user(s) (already have roles): {', '.join(skipped)}"
        
        self.message_user(request, message)
    
    make_driver.short_description = "Assign Driver role to selected users"
    
    def make_warehouse_manager(self, request, queryset):
        """
        Bulk action: Assign Warehouse Manager role to selected users.
        Skips users who already have Driver or WarehouseManager profiles.
        """
        count = 0
        skipped = []
        
        for user in queryset:
            # Skip if already has a role
            if hasattr(user, "driver_profile") or hasattr(user, "warehouse_manager_profile"):
                skipped.append(user.username)
                continue
            
            WarehouseManager.objects.get_or_create(user=user)
            count += 1
        
        message = f"Successfully assigned Warehouse Manager role to {count} user(s)."
        if skipped:
            message += f" Skipped {len(skipped)} user(s) (already have roles): {', '.join(skipped)}"
        
        self.message_user(request, message)
    
    make_warehouse_manager.short_description = "Assign Warehouse Manager role to selected users"
    
    def remove_driver_role(self, request, queryset):
        """
        Bulk action: Remove Driver role from selected users.
        """
        count = 0
        for user in queryset:
            if hasattr(user, "driver_profile"):
                user.driver_profile.delete()
                count += 1
        
        self.message_user(request, f"Successfully removed Driver role from {count} user(s).")
    
    remove_driver_role.short_description = "Remove Driver role from selected users"
    
    def remove_manager_role(self, request, queryset):
        """
        Bulk action: Remove Warehouse Manager role from selected users.
        """
        count = 0
        for user in queryset:
            if hasattr(user, "warehouse_manager_profile"):
                user.warehouse_manager_profile.delete()
                count += 1
        
        self.message_user(request, f"Successfully removed Warehouse Manager role from {count} user(s).")
    
    remove_manager_role.short_description = "Remove Warehouse Manager role from selected users"
    
    def get_inline_instances(self, request, obj=None):
        """
        Show inline forms for both creating and editing users.
        This allows assigning roles immediately when creating a new user.
        """
        return super().get_inline_instances(request, obj)
