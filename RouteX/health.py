"""
Health check endpoint for monitoring and load balancers.
"""
import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint that verifies:
    - Database connectivity
    - Cache connectivity (if Redis is enabled)
    - Application status
    
    Returns 200 if healthy, 503 if unhealthy.
    """
    status = {
        "status": "healthy",
        "database": "unknown",
        "cache": "unknown",
        "version": "1.0.0",
    }
    http_status = 200
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        # Get database engine name for better status message
        db_engine = settings.DATABASES['default']['ENGINE']
        if 'sqlite' in db_engine:
            status["database"] = "connected (SQLite)"
        elif 'postgresql' in db_engine:
            status["database"] = "connected (PostgreSQL)"
        else:
            status["database"] = "connected"
        logger.info("Health check: Database connection OK")
    except Exception as e:
        # More user-friendly error message
        error_msg = str(e)
        if "Connection refused" in error_msg or "5432" in error_msg:
            status["database"] = "error: PostgreSQL not available. Set USE_SQLITE=True in .env to use SQLite."
        else:
            status["database"] = f"error: {error_msg[:100]}"  # Limit error message length
        status["status"] = "unhealthy"
        http_status = 503
        logger.error(f"Health check: Database connection failed - {e}")
    
    # Check cache (if Redis is enabled)
    if getattr(settings, "USE_REDIS", False):
        try:
            cache.set("health_check", "ok", 10)
            cache.get("health_check")
            status["cache"] = "connected"
            logger.info("Health check: Cache connection OK")
        except Exception as e:
            status["cache"] = f"error: {str(e)}"
            # Cache failure is not critical, don't mark as unhealthy
            logger.warning(f"Health check: Cache connection failed - {e}")
    else:
        status["cache"] = "not_configured"
    
    return JsonResponse(status, status=http_status)

