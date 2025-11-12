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
        status["database"] = "connected"
        logger.info("Health check: Database connection OK")
    except Exception as e:
        status["database"] = f"error: {str(e)}"
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

