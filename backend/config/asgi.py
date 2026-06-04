import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# Initialize Django first
django_asgi_app = get_asgi_application()

# Import socketio AFTER Django is set up to prevent AppRegistryNotReady error
from config.socketio import create_socketio_application

application = create_socketio_application(django_asgi_app)
