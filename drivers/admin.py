from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Driver, DriverVerificationDocument, VehicleImage, DriverRating


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        'get_full_name', 'phone_number', 'status_badge', 'vehicle_info',
        'availability_badge', 'total_rides', 'rating_display', 'created_at'
    )
    list_filter = (
        'status', 'background_check_passed', 
        'is_online', 'is_available', 'created_at'
    )
    search_fields = (
        'user__phone_number', 'user__first_name', 'user__last_name', 
        'driver_license_number'
    )
    readonly_fields = (
        'user', 'total_rides', 'completed_rides', 'cancelled_rides',
        'rating', 'total_ratings', 'total_earnings', 'approved_by', 
        'approved_date', 'last_location_update', 'created_at', 'updated_at',
        'license_status', 'can_accept_rides_display', 'current_vehicle_link'
    )
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Vehicle Information', {
            'fields': ('current_vehicle', 'current_vehicle_link')
        }),
        ('Driver License', {
            'fields': ('driver_license_number', 'driver_license_expiry', 'license_status')
        }),
        ('Background Check', {
            'fields': ('background_check_passed', 'background_check_date', 'background_check_notes')
        }),
        ('Application Status', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Availability', {
            'fields': ('is_online', 'is_available', 'last_location_update', 'can_accept_rides_display')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_date')
        }),
        ('Statistics', {
            'fields': (
                'total_rides', 'completed_rides', 'cancelled_rides',
                'rating', 'total_ratings', 'total_earnings'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['approve_drivers', 'reject_drivers', 'suspend_drivers', 'reactivate_drivers']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'user__first_name'
    
    def phone_number(self, obj):
        return obj.user.phone_number
    phone_number.short_description = 'Phone'
    phone_number.admin_order_field = 'user__phone_number'
    
    def vehicle_info(self, obj):
        if obj.current_vehicle:
            return f"{obj.current_vehicle.vehicle_type.name} - {obj.current_vehicle.license_plate}"
        return "No Vehicle"
    vehicle_info.short_description = 'Vehicle'
    
    def current_vehicle_link(self, obj):
        if obj.current_vehicle:
            return format_html(
                '<a href="/admin/vehicles/vehicle/{}/change/">{}</a>',
                obj.current_vehicle.id,
                str(obj.current_vehicle)
            )
        return "No Vehicle Assigned"
    current_vehicle_link.short_description = 'Current Vehicle Details'
    
    def rating_display(self, obj):
        stars = '★' * int(obj.rating)
        rating_value = f"{float(obj.rating):.2f}"
        return format_html(
            '<span style="color: #ffc107;">{}</span> <small>({})</small>',
            stars,
            rating_value
        )
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'rating'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',    # Orange
            'approved': '#28a745',   # Green
            'rejected': '#dc3545',   # Red
            'suspended': '#6c757d',  # Gray
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def availability_badge(self, obj):
        if obj.is_online and obj.is_available:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">🟢 Available</span>'
            )
        elif obj.is_online:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 8px; border-radius: 3px;">🟡 Online</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">⚫ Offline</span>'
        )
    availability_badge.short_description = 'Availability'
    
    def license_status(self, obj):
        if obj.license_expired:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ EXPIRED</span>'
            )
        return format_html(
            '<span style="color: green;">✅ Valid</span>'
        )
    license_status.short_description = 'License Status'
    
    def can_accept_rides_display(self, obj):
        if obj.can_accept_rides:
            return format_html('<span style="color: green;">✅ Yes</span>')
        return format_html('<span style="color: red;">❌ No</span>')
    can_accept_rides_display.short_description = 'Can Accept Rides'
    
    def approve_drivers(self, request, queryset):
        """Approve pending drivers"""
        updated = 0
        for driver in queryset.filter(status='pending'):
            driver.status = 'approved'
            driver.approved_by = request.user
            driver.approved_date = timezone.now()
            driver.save()
            
            # Update user's is_driver flag
            driver.user.is_driver = True
            driver.user.save(update_fields=['is_driver'])
            updated += 1
        
        self.message_user(request, f'{updated} driver(s) approved successfully.')
    approve_drivers.short_description = 'Approve selected drivers'
    
    def reject_drivers(self, request, queryset):
        """Reject pending drivers"""
        updated = 0
        for driver in queryset.filter(status='pending'):
            driver.status = 'rejected'
            driver.approved_by = request.user
            driver.approved_date = timezone.now()
            driver.rejection_reason = driver.rejection_reason or 'Rejected by admin'
            driver.save()
            updated += 1
        
        self.message_user(request, f'{updated} driver(s) rejected.')
    reject_drivers.short_description = 'Reject selected drivers'
    
    def suspend_drivers(self, request, queryset):
        """Suspend drivers"""
        updated = 0
        for driver in queryset.exclude(status='suspended'):
            driver.status = 'suspended'
            driver.is_online = False
            driver.is_available = False
            driver.save()
            updated += 1
        
        self.message_user(request, f'{updated} driver(s) suspended.')
    suspend_drivers.short_description = 'Suspend selected drivers'
    
    def reactivate_drivers(self, request, queryset):
        """Reactivate suspended drivers"""
        updated = 0
        for driver in queryset.filter(status='suspended'):
            driver.status = 'approved'
            driver.save()
            updated += 1
        
        self.message_user(request, f'{updated} driver(s) reactivated.')
    reactivate_drivers.short_description = 'Reactivate suspended drivers'


@admin.register(DriverVerificationDocument)
class DriverVerificationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'get_driver_name', 'document_type_display', 'get_file_size', 
        'is_verified_badge', 'verified_by', 'uploaded_at'
    )
    list_filter = ('document_type', 'is_verified', 'uploaded_at')
    search_fields = (
        'driver__user__phone_number', 'driver__user__first_name', 
        'driver__user__last_name'
    )
    readonly_fields = (
        'driver', 'uploaded_at', 'updated_at', 'verified_date', 'document_preview'
    )
    
    fieldsets = (
        ('Document Information', {
            'fields': ('driver', 'document_type', 'document', 'document_preview')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_date', 'notes')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'updated_at')
        }),
    )
    
    actions = ['mark_as_verified', 'mark_as_unverified']
    
    def get_driver_name(self, obj):
        return obj.driver.user.get_full_name()
    get_driver_name.short_description = 'Driver'
    get_driver_name.admin_order_field = 'driver__user__first_name'
    
    def document_type_display(self, obj):
        return obj.get_document_type_display()
    document_type_display.short_description = 'Document Type'
    document_type_display.admin_order_field = 'document_type'
    
    def get_file_size(self, obj):
        if obj.document:
            size_bytes = obj.document.size
            size_mb = size_bytes / (1024 * 1024)
            return f'{size_mb:.2f} MB'
        return 'N/A'
    get_file_size.short_description = 'File Size'
    
    def is_verified_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">✅ Verified</span>'
            )
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">⏳ Pending</span>'
        )
    is_verified_badge.short_description = 'Status'
    is_verified_badge.admin_order_field = 'is_verified'
    
    def document_preview(self, obj):
        if obj.document:
            return format_html(
                '<a href="{}" target="_blank" style="padding: 5px 10px; background: #007bff; color: white; text-decoration: none; border-radius: 3px;">📄 View Document</a>',
                obj.document.url
            )
        return 'No document'
    document_preview.short_description = 'Preview'
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(
            is_verified=True,
            verified_by=request.user,
            verified_date=timezone.now()
        )
        self.message_user(request, f'{updated} document(s) marked as verified.')
    mark_as_verified.short_description = 'Mark as verified'
    
    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(
            is_verified=False,
            verified_by=None,
            verified_date=None
        )
        self.message_user(request, f'{updated} document(s) marked as unverified.')
    mark_as_unverified.short_description = 'Mark as unverified'


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = (
        'get_driver_name', 'image_type_display', 'image_preview_thumb', 'uploaded_at'
    )
    list_filter = ('image_type', 'uploaded_at')
    search_fields = (
        'driver__user__phone_number', 'driver__user__first_name', 
        'driver__user__last_name'
    )
    readonly_fields = ('driver', 'uploaded_at', 'image_preview')
    
    fieldsets = (
        ('Image Information', {
            'fields': ('driver', 'image_type', 'image', 'image_preview')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at',)
        }),
    )
    
    def get_driver_name(self, obj):
        return obj.driver.user.get_full_name()
    get_driver_name.short_description = 'Driver'
    get_driver_name.admin_order_field = 'driver__user__first_name'
    
    def image_type_display(self, obj):
        return obj.get_image_type_display()
    image_type_display.short_description = 'Image Type'
    image_type_display.admin_order_field = 'image_type'
    
    def image_preview_thumb(self, obj):
        """Thumbnail for list view"""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;"/>',
                obj.image.url
            )
        return '📷'
    image_preview_thumb.short_description = 'Preview'
    
    def image_preview(self, obj):
        """Full preview for detail view"""
        if obj.image:
            return format_html(
                '<img src="{}" width="300" style="object-fit: contain; border-radius: 5px; border: 1px solid #ddd;"/>',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Image Preview'


@admin.register(DriverRating)
class DriverRatingAdmin(admin.ModelAdmin):
    list_display = (
        'get_driver_name', 'get_rider_name', 'rating_stars', 
        'has_comment', 'created_at'
    )
    list_filter = ('rating', 'created_at')
    search_fields = (
        'driver__user__phone_number', 'driver__user__first_name',
        'rider__phone_number', 'rider__first_name'
    )
    readonly_fields = ('driver', 'rider', 'ride', 'rating', 'created_at')
    
    fieldsets = (
        ('Rating Information', {
            'fields': ('driver', 'rider', 'ride', 'rating')
        }),
        ('Comment', {
            'fields': ('comment',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_driver_name(self, obj):
        return obj.driver.user.get_full_name()
    get_driver_name.short_description = 'Driver'
    get_driver_name.admin_order_field = 'driver__user__first_name'
    
    def get_rider_name(self, obj):
        return obj.rider.get_full_name() if obj.rider else 'Unknown'
    get_rider_name.short_description = 'Rider'
    get_rider_name.admin_order_field = 'rider__first_name'
    
    def rating_stars(self, obj):
        full_stars = int(obj.rating)
        half_star = (obj.rating - full_stars) >= 0.5
        stars = '★' * full_stars
        if half_star:
            stars += '½'
        return format_html(
            '<span style="color: #ffc107; font-size: 16px;">{}</span> <small>({:.1f})</small>',
            stars,
            float(obj.rating)
        )
    rating_stars.short_description = 'Rating'
    rating_stars.admin_order_field = 'rating'
    
    def has_comment(self, obj):
        if obj.comment:
            return format_html('<span style="color: green;">✅</span>')
        return format_html('<span style="color: gray;">—</span>')
    has_comment.short_description = 'Comment'