# 📍 LOCATIONS APP

Real-time GPS tracking, geofencing, and location management for ride-hailing platform.

---

## 🎯 **PURPOSE:**

The locations app handles:
- **Real-time driver tracking** - Live GPS positions
- **Ride route tracking** - Complete trip history
- **Geofencing** - Proximity alerts (driver arriving, etc.)
- **Location history** - Saved & recent locations
- **Distance calculations** - Haversine formula
- **ETA calculations** - Time estimates

---

## 📊 **MODELS:**

### **1. SavedLocation**
User's favorite locations (home, work, etc.)

**Fields:**
- `user` - Owner
- `location_type` - home/work/other
- `address` - Full address
- `latitude`, `longitude` - Coordinates
- `landmark` - Optional landmark
- `instructions` - Special instructions
- `is_active` - Status

**Usage:**
```python
# Save home location
SavedLocation.objects.create(
    user=user,
    location_type='home',
    address='123 Main St, Lagos',
    latitude=6.5244,
    longitude=3.3792
)
```

### **2. RecentLocation**
Recently used addresses for auto-suggestions

**Fields:**
- `user` - Owner
- `address` - Address
- `latitude`, `longitude` - Coordinates
- `search_count` - Usage count
- `last_used` - Timestamp

**Usage:**
```python
# Add recent location
location, created = RecentLocation.objects.get_or_create(
    user=user,
    address=address,
    defaults={'latitude': lat, 'longitude': lng}
)
if not created:
    location.search_count += 1
    location.save()
```

### **3. DriverLocation**
Real-time driver GPS position (OneToOne)

**Fields:**
- `driver` - Driver (OneToOne)
- `latitude`, `longitude` - Current position
- `bearing` - Direction (0-360°)
- `speed_kmh` - Speed
- `accuracy_meters` - GPS accuracy
- `last_updated` - Timestamp

**Properties:**
- `coordinates` - Returns (lat, lng) tuple
- `is_stale` - True if > 5 minutes old

**Usage:**
```python
# Update driver location
driver_loc, created = DriverLocation.objects.update_or_create(
    driver=driver,
    defaults={
        'latitude': lat,
        'longitude': lng,
        'speed_kmh': speed,
        'bearing': bearing
    }
)
```

### **4. RideTracking**
GPS breadcrumb trail during rides

**Fields:**
- `ride` - Ride being tracked
- `latitude`, `longitude` - Point coordinates
- `speed_kmh` - Speed at point
- `bearing` - Direction at point
- `accuracy_meters` - GPS accuracy
- `timestamp` - When recorded

**Usage:**
```python
# Track ride point
RideTracking.objects.create(
    ride=ride,
    latitude=lat,
    longitude=lng,
    speed_kmh=speed,
    bearing=bearing
)
```

---

## 🔗 **INTEGRATIONS:**

### **RIDES APP:**
```python
# When ride starts:
→ Tracking begins automatically
→ RideTracking points created

# When ride completes:
→ Calculate actual distance
→ Verify fare
```

### **DRIVERS APP:**
```python
# When driver goes online:
→ DriverLocation created
→ GPS tracking active

# Every location update:
→ Check for active rides
→ Trigger geofence events
```

### **NOTIFICATIONS APP:**
```python
# Geofence triggers:
Driver < 2km → "Driver approaching"
Driver < 100m → "Driver arrived" (Push + SMS)
```

### **PRICING APP:**
```python
# Distance calculations:
→ Uses locations.calculate_distance()
→ Fare estimates based on route
```

---

## 📡 **API ENDPOINTS:**

### **Saved Locations:**
```
GET    /api/locations/saved/           # List saved locations
POST   /api/locations/saved/           # Create saved location
GET    /api/locations/saved/{id}/      # Get saved location
PUT    /api/locations/saved/{id}/      # Update saved location
DELETE /api/locations/saved/{id}/      # Delete saved location
```

### **Recent Locations:**
```
GET    /api/locations/recent/          # List recent locations (last 10)
POST   /api/locations/recent/add/      # Add/update recent location
```

### **Driver Tracking:**
```
POST   /api/locations/driver/update/   # Update driver GPS position
GET    /api/locations/driver/nearby/   # Find nearby drivers
```

**Request Body (update):**
```json
{
  "latitude": 6.5244,
  "longitude": 3.3792,
  "bearing": 45.5,
  "speed_kmh": 35.2,
  "accuracy_meters": 10.5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Location updated",
  "data": {
    "latitude": 6.5244,
    "longitude": 3.3792,
    "last_updated": "2024-11-03T12:34:56Z"
  }
}
```

### **Ride Tracking:**
```
POST   /api/locations/ride/track/      # Track ride location point
GET    /api/locations/ride/{id}/route/ # Get complete ride route
```

### **Utilities:**
```
POST   /api/locations/detect-city/     # Detect city from coordinates
```

---

## 🚀 **SERVICES:**

### **calculate_distance(lat1, lon1, lat2, lon2)**
Calculate distance between two coordinates using Haversine formula.

**Returns:** Distance in kilometers

```python
from locations.services import calculate_distance

distance = calculate_distance(6.5244, 3.3792, 6.4281, 3.4219)
# Returns: 12.34 km
```

### **update_driver_location(driver, lat, lng, ...)**
Update driver's current GPS position.

**Returns:** DriverLocation object

```python
from locations.services import update_driver_location

location = update_driver_location(
    driver=driver,
    latitude=6.5244,
    longitude=3.3792,
    speed_kmh=45.0,
    bearing=90.0
)
```

### **get_nearby_drivers(lat, lng, radius_km, vehicle_type)**
Find nearby online drivers within radius.

**Returns:** List of drivers with distances

```python
from locations.services import get_nearby_drivers

nearby = get_nearby_drivers(
    latitude=6.5244,
    longitude=3.3792,
    radius_km=10,
    vehicle_type='car'
)

# Returns:
# [
#   {
#     'driver': Driver object,
#     'driver_location': DriverLocation object,
#     'distance_km': 2.5,
#     'latitude': 6.5200,
#     'longitude': 3.3800
#   },
#   ...
# ]
```

### **calculate_eta(driver_location, dest_lat, dest_lng)**
Calculate estimated time of arrival.

**Returns:** ETA information

```python
from locations.services import calculate_eta

eta = calculate_eta(driver_location, 6.5244, 3.3792)

# Returns:
# {
#   'distance_km': 5.2,
#   'eta_minutes': 12,
#   'eta_formatted': '12 mins'
# }
```

### **track_ride_location(ride, lat, lng, ...)**
Record GPS point during ride.

**Returns:** RideTracking object

### **calculate_route_distance(tracking_points)**
Calculate total distance from tracking points.

**Returns:** Total distance in kilometers

```python
from locations.services import calculate_route_distance

tracking_points = RideTracking.objects.filter(ride=ride)
distance = calculate_route_distance(tracking_points)
# Returns: 12.34 km
```

### **check_geofence(lat, lng, center_lat, center_lng, radius_m)**
Check if point is within geofence.

**Returns:** (is_inside, distance_meters)

```python
from locations.services import check_geofence

is_inside, distance = check_geofence(
    latitude=6.5244,
    longitude=3.3792,
    center_lat=6.5240,
    center_lng=3.3790,
    radius_meters=100
)
# Returns: (True, 45.2) or (False, 150.3)
```

---

## 🔧 **SIGNALS:**

### **driver_online_status_handler**
When driver goes online, create DriverLocation.

### **ride_tracking_handler**
When ride starts, begin tracking. When completes, calculate distance.

### **driver_location_updated_handler**
Check for geofence events and trigger notifications.

### **track_active_ride_route**
Automatically record tracking points during ride.

---

## ⏰ **CELERY TASKS:**

### **cleanup_old_ride_tracking**
Delete tracking points older than 30 days.

**Schedule:** Daily

### **update_inactive_drivers**
Mark drivers offline if location hasn't updated in 10 minutes.

**Schedule:** Every 5 minutes

### **generate_location_statistics**
Generate daily location statistics.

**Schedule:** Daily

---

## 📱 **CLIENT USAGE:**

### **Update Driver Location (Every 5-10 seconds):**
```javascript
// Driver app sends GPS updates
const updateLocation = async (position) => {
  await fetch('/api/locations/driver/update/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      bearing: position.coords.heading,
      speed_kmh: position.coords.speed * 3.6, // m/s to km/h
      accuracy_meters: position.coords.accuracy
    })
  });
};

// Start tracking
navigator.geolocation.watchPosition(updateLocation, null, {
  enableHighAccuracy: true,
  maximumAge: 0
});
```

### **Get Nearby Drivers:**
```javascript
const findNearbyDrivers = async (lat, lng) => {
  const response = await fetch(
    `/api/locations/driver/nearby/?latitude=${lat}&longitude=${lng}&radius=10`,
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  
  const data = await response.json();
  // Display drivers on map
  displayDriversOnMap(data.drivers);
};
```

### **Track Ride Route:**
```javascript
const trackRide = async (rideId) => {
  const response = await fetch(`/api/locations/ride/${rideId}/route/`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data = await response.json();
  // Display route on map
  displayRouteOnMap(data.route);
};
```

---

## 🎯 **GEOFENCING:**

### **Automatic Triggers:**

**Driver Approaching (2km radius):**
```python
# When driver within 2km of pickup:
→ Notification sent to rider
→ "Driver is 5 minutes away"
```

**Driver Arrived (100m radius):**
```python
# When driver within 100m of pickup:
→ ride.status = 'driver_arrived'
→ Push notification + SMS sent
→ "Driver has arrived at pickup location"
```

---

## ✅ **FEATURES:**

- ✅ Real-time driver GPS tracking
- ✅ Find drivers within radius
- ✅ Distance & ETA calculations
- ✅ Ride route tracking
- ✅ Geofencing & proximity alerts
- ✅ Saved locations (home, work)
- ✅ Recent location suggestions
- ✅ Actual distance verification
- ✅ Google Maps integration
- ✅ Auto-cleanup old data

---

## 🏆 **PRODUCTION-READY!**

**Complete GPS tracking system!**
**Automatic geofence notifications!**
**Fully integrated with all apps!**