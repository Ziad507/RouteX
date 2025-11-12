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
    verbose_name = "🚗 Driver Profile"
    verbose_name_plural = "🚗 Driver Profile"
    fk_name = "user"
    fields = ("is_active",)
    extra = 0
    max_num = 1
    
    def get_extra(self, request, obj=None, **kwargs):
        """Don't show extra empty forms."""
        return 0


class WarehouseManagerInline(admin.StackedInline):
    """
    Inline form to manage WarehouseManager profile directly from User admin page.
    Allows assigning warehouse manager role without navigating to separate page.
    """
    model = WarehouseManager
    can_delete = True
    verbose_name = "📦 Warehouse Manager Profile"
    verbose_name_plural = "📦 Warehouse Manager Profile"
    fk_name = "user"
    fields = ()  # No additional fields, just the relationship
    extra = 0
    max_num = 1
    
    def get_extra(self, request, obj=None, **kwargs):
        """Don't show extra empty forms."""
        return 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Enhanced User admin with role management (Driver/WarehouseManager) via inline forms.
    Supports creating, editing, and deleting users with automatic role assignment.
    """
    # Inline forms for role management
    inlines = [DriverInline, WarehouseManagerInline]
    
    # Field organization for editing existing users
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Contact Information", {"fields": ("phone",)}),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    
    # Field organization for creating new users (clean, no duplication)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2"),
            "description": "Enter the username and password for the new user. The password must meet security requirements.",
        }),
        ("Contact Information", {
            "fields": ("phone",),
            "description": "Enter the user's phone number. Must be unique and in Saudi format (+966XXXXXXXXX).",
        }),
        ("Permissions", {
            "fields": ("is_staff", "is_active"),
            "description": "Set user permissions. Staff users can access the admin panel. Active users can log in.",
        }),
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
        Only show inline forms when editing existing users.
        This prevents errors when creating new users (user must exist first).
        """
        if not obj:
            return []
        return super().get_inline_instances(request, obj)
    
    def save_model(self, request, obj, form, change):
        """
        Save the user model and handle role assignment after user creation.
        """
        super().save_model(request, obj, form, change)
        
        # After saving, if this is a new user and no role was assigned via inline,
        # we can optionally assign a default role here if needed
        # For now, roles are assigned via inline forms or bulk actions
