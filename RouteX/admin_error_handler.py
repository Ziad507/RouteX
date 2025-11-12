"""
Admin error handler middleware and views for displaying errors in admin panel.
"""
import logging
import traceback
from django.http import HttpResponseServerError
from django.template import loader
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.html import format_html
from django.urls import path
from pathlib import Path

logger = logging.getLogger("admin")


class AdminErrorLoggingMiddleware:
    """
    Middleware to log all errors in admin panel and store them for display.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log admin errors
        if request.path.startswith("/api/admin/") and response.status_code >= 500:
            logger.error(
                f"Admin Error: {request.path} | Status: {response.status_code} | "
                f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'} | "
                f"Method: {request.method}"
            )
        
        return response
    
    def process_exception(self, request, exception):
        """
        Log exceptions that occur in admin panel.
        """
        if request.path.startswith("/api/admin/"):
            error_trace = traceback.format_exc()
            logger.error(
                f"Admin Exception: {request.path}\n"
                f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}\n"
                f"Exception: {type(exception).__name__}: {str(exception)}\n"
                f"Traceback:\n{error_trace}"
            )
        
        # Don't interfere with Django's exception handling
        # Return None to let Django handle it normally
        return None


def get_recent_errors(log_file_path: Path, lines: int = 50) -> list:
    """
    Read recent error lines from log file.
    """
    errors = []
    try:
        if log_file_path.exists():
            with open(log_file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                # Get last N lines
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                errors = [line.strip() for line in recent_lines if line.strip()]
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
    
    return errors


@staff_member_required
@require_http_methods(["GET"])
def admin_error_logs_view(request):
    """
    Display recent admin errors in admin panel.
    """
    from django.conf import settings
    from django.shortcuts import render
    
    logs_dir = getattr(settings, "LOGS_DIR", Path(settings.BASE_DIR) / "logs")
    admin_log_file = logs_dir / "admin.log"
    errors_log_file = logs_dir / "errors.log"
    django_log_file = logs_dir / "django.log"
    
    admin_errors = get_recent_errors(admin_log_file, lines=30)
    all_errors = get_recent_errors(errors_log_file, lines=50)
    django_logs = get_recent_errors(django_log_file, lines=30)
    
    context = {
        "title": "Error Logs",
        "admin_errors": admin_errors,
        "all_errors": all_errors,
        "django_logs": django_logs,
        "admin_log_file": str(admin_log_file),
        "errors_log_file": str(errors_log_file),
        "django_log_file": str(django_log_file),
    }
    
    return render(request, "admin/error_logs.html", context)


def admin_error_logs_url():
    """
    URL pattern for admin error logs view.
    """
    return path("admin/error-logs/", admin_error_logs_view, name="admin_error_logs")

