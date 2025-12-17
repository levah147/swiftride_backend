"""
FILE LOCATION: swiftride/routing.py

✅ CRITICAL FIX #1: WebSocket URL Routing for SwiftRide
This file combines all WebSocket routes from different apps.

WHAT THIS FIXES:
- Currently, asgi.py only uses chat.routing.websocket_urlpatterns
- Rides WebSocket routes are imported but NEVER used
- This causes rides WebSocket to NOT work at all

INSTRUCTIONS:
1. Create this file at: swiftride/routing.py
2. Then update asgi.py to use this routing (see Fix #2)
"""

from channels.routing import URLRouter
from django.urls import path

# Import WebSocket URL patterns from apps
try:
    from rides.routing import websocket_urlpatterns as rides_ws_urls
except ImportError:
    rides_ws_urls = []
    print("⚠️ Warning: rides.routing not found. Rides WebSocket will not work.")

try:
    from chat.routing import websocket_urlpatterns as chat_ws_urls
except ImportError:
    chat_ws_urls = []
    print("⚠️ Warning: chat.routing not found. Chat WebSocket will not work.")

# ✅ Combine all WebSocket URL patterns
websocket_urlpatterns = [
    # Rides WebSocket routes
    # Example: ws://localhost:8000/ws/ride/123/?token=abc...
    *rides_ws_urls,
    
    # Chat WebSocket routes
    # Example: ws://localhost:8000/ws/chat/456/?token=abc...
    *chat_ws_urls,
]

# Debug: Print registered WebSocket routes
if __name__ != '__main__':
    print(f"✅ Registered {len(websocket_urlpatterns)} WebSocket routes:")
    for pattern in websocket_urlpatterns:
        print(f"   - {pattern.pattern}")