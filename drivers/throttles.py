"""
FILE LOCATION: drivers/throttles.py

Custom throttle classes for driver operations.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class DriverApplicationThrottle(AnonRateThrottle):
    """
    Throttle for driver application submission.
    Limit: 1 application per day per IP address.
    """
    rate = '1/day'
    scope = 'driver_application'


class DriverStatusChangeThrottle(UserRateThrottle):
    """
    Throttle for driver status changes (online/offline).
    Limit: 20 status changes per hour per user.
    """
    rate = '20/hour'
    scope = 'driver_status_change'


class DocumentUploadThrottle(UserRateThrottle):
    """
    Throttle for document uploads.
    Limit: 10 uploads per hour per user.
    """
    rate = '10/hour'
    scope = 'document_upload'
