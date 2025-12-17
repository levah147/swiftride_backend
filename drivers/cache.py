"""
FILE LOCATION: drivers/cache.py

Caching utilities for driver queries to improve performance.
"""
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class DriverCache:
    """Cache manager for driver-related queries"""
    
    # Cache key prefixes
    DRIVER_AVAILABILITY_PREFIX = 'driver_availability'
    DRIVER_SCORE_PREFIX = 'driver_score'
    NEARBY_DRIVERS_PREFIX = 'nearby_drivers'
    
    # Cache timeouts (in seconds)
    AVAILABILITY_TIMEOUT = 300  # 5 minutes
    SCORE_TIMEOUT = 600  # 10 minutes
    NEARBY_TIMEOUT = 180  # 3 minutes
    
    @staticmethod
    def get_driver_availability(driver_id):
        """Get cached driver availability status"""
        key = f"{DriverCache.DRIVER_AVAILABILITY_PREFIX}_{driver_id}"
        return cache.get(key)
    
    @staticmethod
    def set_driver_availability(driver_id, is_available, is_online):
        """Cache driver availability status"""
        key = f"{DriverCache.DRIVER_AVAILABILITY_PREFIX}_{driver_id}"
        value = {'is_available': is_available, 'is_online': is_online}
        cache.set(key, value, DriverCache.AVAILABILITY_TIMEOUT)
        logger.debug(f"Cached availability for driver {driver_id}")
    
    @staticmethod
    def invalidate_driver_availability(driver_id):
        """Invalidate driver availability cache"""
        key = f"{DriverCache.DRIVER_AVAILABILITY_PREFIX}_{driver_id}"
        cache.delete(key)
        logger.debug(f"Invalidated availability cache for driver {driver_id}")
    
    @staticmethod
    def get_driver_score(driver_id):
        """Get cached driver score"""
        key = f"{DriverCache.DRIVER_SCORE_PREFIX}_{driver_id}"
        return cache.get(key)
    
    @staticmethod
    def set_driver_score(driver_id, score):
        """Cache driver score"""
        key = f"{DriverCache.DRIVER_SCORE_PREFIX}_{driver_id}"
        cache.set(key, score, DriverCache.SCORE_TIMEOUT)
        logger.debug(f"Cached score for driver {driver_id}: {score}")
    
    @staticmethod
    def invalidate_driver_score(driver_id):
        """Invalidate driver score cache"""
        key = f"{DriverCache.DRIVER_SCORE_PREFIX}_{driver_id}"
        cache.delete(key)
    
    @staticmethod
    def get_nearby_drivers(lat, lng, radius_km):
        \"\"\"Get cached nearby drivers list\"\"\"
        # Round coordinates to reduce cache keys
        lat_rounded = round(float(lat), 3)  # ~111m precision
        lng_rounded = round(float(lng), 3)
        
        key = f"{DriverCache.NEARBY_DRIVERS_PREFIX}_{lat_rounded}_{lng_rounded}_{radius_km}"
        return cache.get(key)
    
    @staticmethod
    def set_nearby_drivers(lat, lng, radius_km, driver_ids):
        \"\"\"Cache nearby drivers list\"\"\"
        lat_rounded = round(float(lat), 3)
        lng_rounded = round(float(lng), 3)
        
        key = f"{DriverCache.NEARBY_DRIVERS_PREFIX}_{lat_rounded}_{lng_rounded}_{radius_km}"
        cache.set(key, driver_ids, DriverCache.NEARBY_TIMEOUT)
        logger.debug(f"Cached {len(driver_ids)} nearby drivers for ({lat_rounded}, {lng_rounded})")
    
    @staticmethod
    def clear_all_driver_caches():
        \"\"\"Clear all driver-related caches (use sparingly)\"\"\"
        # This is implemented differently depending on your cache backend
        # For Redis: cache.delete_pattern()
        # For simple backend: just log
        logger.warning("clear_all_driver_caches called - implement based on cache backend")
