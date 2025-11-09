from django.contrib import admin
from .models import Ride, RideRequest, DriverRideResponse, MutualRating, Promotion


# -----------------------------
# Inline Admins
# -----------------------------
class DriverRideResponseInline(admin.TabularInline):
    model = DriverRideResponse
    extra = 0
    readonly_fields = ('driver', 'response', 'decline_reason', 'response_time_seconds', 'created_at')
    can_delete = False


class RideRequestInline(admin.TabularInline):
    model = RideRequest
    extra = 0
    readonly_fields = ('status', 'expires_at', 'created_at', 'updated_at')
    can_delete = False
    show_change_link = True


class MutualRatingInline(admin.StackedInline):
    model = MutualRating
    extra = 0
    readonly_fields = (
        'rider_rating',
        'rider_comment',
        'driver_rating',
        'driver_comment',
        'rider_rated_at',
        'driver_rated_at',
        'created_at',
        'updated_at',
    )


# -----------------------------
# Ride Admin
# -----------------------------
@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'driver',
        'status',
        'ride_type',
        'city',
        'fare_amount',
        'distance_km',
        'created_at',
    )
    list_filter = (
        'status',
        'ride_type',
        'city',
        'vehicle_type',
        'created_at',
    )
    search_fields = (
        'id',
        'user__phone_number',
        'driver__user__phone_number',
        'pickup_location',
        'destination_location',
    )
    inlines = [RideRequestInline, MutualRatingInline]
    readonly_fields = ('created_at', 'updated_at', 'accepted_at', 'started_at', 'completed_at', 'cancelled_at')
    date_hierarchy = 'created_at'
    list_per_page = 25


# -----------------------------
# Ride Request Admin
# -----------------------------
@admin.register(RideRequest)
class RideRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'ride', 'status', 'expires_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('ride__id', 'ride__user__phone_number', 'ride__driver__user__phone_number')
    inlines = [DriverRideResponseInline]
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


# -----------------------------
# Driver Ride Response Admin
# -----------------------------
@admin.register(DriverRideResponse)
class DriverRideResponseAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'ride_request',
        'driver',
        'response',
        'response_time_seconds',
        'created_at',
    )
    list_filter = ('response',)
    search_fields = ('driver__user__phone_number', 'ride_request__ride__id')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


# -----------------------------
# Mutual Rating Admin
# -----------------------------
@admin.register(MutualRating)
class MutualRatingAdmin(admin.ModelAdmin):
    list_display = (
        'ride',
        'rider_rating',
        'driver_rating',
        'is_complete',
        'created_at',
    )
    list_filter = ('rider_rating', 'driver_rating')
    search_fields = ('ride__id', 'ride__user__phone_number', 'ride__driver__user__phone_number')
    readonly_fields = ('created_at', 'updated_at', 'rider_rated_at', 'driver_rated_at')
    date_hierarchy = 'created_at'


# -----------------------------
# Promotion Admin
# -----------------------------
@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'discount_percentage',
        'max_rides',
        'is_active',
        'valid_from',
        'valid_until',
        'created_at',
    )
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'valid_from'
