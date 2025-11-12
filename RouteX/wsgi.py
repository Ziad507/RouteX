"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

# Add project directory to Python path dynamically
BASE_DIR = Path(__file__).resolve().parent.parent
project_path = str(BASE_DIR)
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RouteX.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
