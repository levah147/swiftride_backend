"""
FILE LOCATION: swiftride/asgi.py

✅ CRITICAL FIX #2: ASGI Configuration for SwiftRide

WHAT THIS FIXES:
- OLD: Only uses chat.routing.websocket_urlpatterns (rides WebSocket doesn't work)
- NEW: Uses combined routing from swiftride/routing.py (both chat and rides work)
- Removes duplicate imports
- Proper initialization order

INSTRUCTIONS:
1. REPLACE your current swiftride/asgi.py with this file
2. Make sure swiftride/routing.py exists (Fix #1)
3. Restart Django server and Channels workers
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swiftride.settings')

# ✅ STEP 1: Initialize Django ASGI application FIRST
# This ensures all apps are loaded before importing routing
django_asgi_app = get_asgi_application()

# ✅ STEP 2: Import WebSocket routing AFTER Django is initialized
# This prevents AppRegistryNotReady errors
from swiftride.routing import websocket_urlpatterns

# ✅ STEP 3: Configure Protocol Router
application = ProtocolTypeRouter({
    # Handle HTTP requests
    "http": django_asgi_app,
    
    # Handle WebSocket connections
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns  # ✅ Uses BOTH rides and chat WebSocket routes
        )
    ),
})

print("✅ ASGI application configured successfully!")
print(f"✅ WebSocket routes: {len(websocket_urlpatterns)} registered")



# # swiftride/asgi.py
# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from chat import routing
# from rides.routing import websocket_urlpatterns


# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swiftride.settings')

# # Initialize Django ASGI application early to ensure apps are loaded
# django_asgi_app = get_asgi_application()

# # Import after Django is initialized
# from rides.routing import websocket_urlpatterns

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             routing.websocket_urlpatterns
#         )
#     ),
# })




