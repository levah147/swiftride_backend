#   views.py for drivers app



from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from .models import Driver, DriverVerificationDocument, VehicleImage, DriverRating
from accounts.models import User
from .serializers import (
    DriverApplicationSerializer,
    DriverProfileSerializer,
    DriverStatusSerializer,
    AdminDriverApprovalSerializer,
    DriverVerificationDocumentSerializer,
    VehicleImageSerializer,
    DriverRatingSerializer
)
from .throttles import (
    DriverApplicationThrottle,
    DriverStatusChangeThrottle,
    DocumentUploadThrottle
)


# Replace your DriverApplicationView with this updated version 

class DriverApplicationView(generics.CreateAPIView):
    """Apply to become a driver"""
    serializer_class = DriverApplicationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [DriverApplicationThrottle]  # Limit: 1 application/day
    
    def create(self, request, *args, **kwargs):
        # Check if user already has a driver application
        if hasattr(request.user, 'driver_profile'):
            driver = request.user.driver_profile
            return Response(
                {
                    'error': 'You already have a driver application.',
                    'status': driver.status,
                    'message': f'Your application is currently {driver.get_status_display().lower()}.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate request data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create driver profile with vehicle
        try:
            driver = serializer.save()
            
            return Response(
                {
                    'message': 'Driver application submitted successfully',
                    'driver': DriverProfileSerializer(
                        driver, 
                        context={'request': request}
                    ).data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create driver profile: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
class DriverProfileView(generics.RetrieveUpdateAPIView):
    """Get/update current user's driver profile"""
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        try:
            return self.request.user.driver_profile
        except Driver.DoesNotExist:
            return None
    
    def retrieve(self, request, *args, **kwargs):
        driver = self.get_object()
        if driver is None:
            return Response(
                {
                    'is_driver': False,
                    'message': 'You have not applied to become a driver yet.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(driver)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        driver = self.get_object()
        if driver is None:
            return Response(
                {'error': 'You do not have a driver profile.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prevent updating sensitive fields
        protected_fields = [
            'status', 'background_check_passed', 'total_rides', 
            'rating', 'approved_by', 'approved_date', 'is_online',
            'is_available', 'total_earnings'
        ]
        
        for field in protected_fields:
            if field in request.data:
                return Response(
                    {'error': f'You cannot update the "{field}" field.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Don't allow updates if approved (except specific fields)
        if driver.is_approved:
            allowed_fields = ['vehicle_color', 'driver_license_expiry']
            for field in request.data:
                if field not in allowed_fields:
                    return Response(
                        {
                            'error': 'You can only update vehicle color and license expiry after approval.',
                            'allowed_fields': allowed_fields
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        serializer = self.get_serializer(driver, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


class UploadVerificationDocumentView(generics.CreateAPIView):
    """Upload driver verification documents"""
    serializer_class = DriverVerificationDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = [DocumentUploadThrottle]  # Limit: 10 uploads/hour
    
    def create(self, request, *args, **kwargs):
        try:
            driver = request.user.driver_profile
        except Driver.DoesNotExist:
            return Response(
                {'error': 'You do not have a driver profile. Please apply first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Don't allow document upload if already approved
        if driver.is_approved:
            return Response(
                {'error': 'Cannot upload documents after approval. Contact support if you need to update documents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        document_type = request.data.get('document_type')
        document_file = request.FILES.get('document')
        
        if not document_type:
            return Response(
                {'error': 'document_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not document_file:
            return Response(
                {'error': 'document file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 10MB)
        if document_file.size > 10 * 1024 * 1024:
            return Response(
                {'error': 'Document file size must not exceed 10MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Delete existing document of same type
                DriverVerificationDocument.objects.filter(
                    driver=driver,
                    document_type=document_type
                ).delete()
                
                # Create new document
                doc = DriverVerificationDocument.objects.create(
                    driver=driver,
                    document_type=document_type,
                    document=document_file
                )
                
                return Response(
                    DriverVerificationDocumentSerializer(
                        doc, 
                        context={'request': request}
                    ).data,
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            return Response(
                {'error': f'Failed to upload document: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class UploadVehicleImageView(generics.CreateAPIView):
    """Upload vehicle images"""
    serializer_class = VehicleImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    throttle_classes = [DocumentUploadThrottle]  # Limit: 10 uploads/hour
    
    def create(self, request, *args, **kwargs):
        try:
            driver = request.user.driver_profile
        except Driver.DoesNotExist:
            return Response(
                {'error': 'You do not have a driver profile. Please apply first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        image_type = request.data.get('image_type')
        image_file = request.FILES.get('image')
        
        if not image_type:
            return Response(
                {'error': 'image_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not image_file:
            return Response(
                {'error': 'image file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'Image file size must not exceed 5MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Delete existing image of same type
                VehicleImage.objects.filter(
                    driver=driver,
                    image_type=image_type
                ).delete()
                
                # Create new image
                image = VehicleImage.objects.create(
                    driver=driver,
                    image_type=image_type,
                    image=image_file
                )
                
                return Response(
                    VehicleImageSerializer(
                        image, 
                        context={'request': request}
                    ).data,
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            return Response(
                {'error': f'Failed to upload image: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class DriverStatusView(generics.RetrieveAPIView):
    """Check if current user is a driver and their status"""
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, *args, **kwargs):
        try:
            driver = request.user.driver_profile
            serializer = DriverStatusSerializer(driver)
            return Response({
                'is_driver': True,
                'driver': serializer.data
            }, status=status.HTTP_200_OK)
        except Driver.DoesNotExist:
            return Response(
                {
                    'is_driver': False,
                    'message': 'You have not applied to become a driver yet.'
                },
                status=status.HTTP_200_OK
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_driver_documents_status(request):
    """Get status of all driver documents"""
    try:
        driver = request.user.driver_profile
        
        documents = driver.verification_documents.all()
        images = driver.vehicle_images.all()
        
        total_docs = documents.count()
        verified_docs = documents.filter(is_verified=True).count()
        total_images = images.count()
        
        # Required documents
        required_docs = ['license', 'registration', 'insurance', 'id_card']
        required_images = ['front', 'back', 'left_side', 'right_side', 'interior', 'registration']
        
        uploaded_doc_types = list(documents.values_list('document_type', flat=True))
        uploaded_image_types = list(images.values_list('image_type', flat=True))
        
        missing_docs = [doc for doc in required_docs if doc not in uploaded_doc_types]
        missing_images = [img for img in required_images if img not in uploaded_image_types]
        
        all_required_uploaded = len(missing_docs) == 0 and len(missing_images) == 0
        all_docs_verified = total_docs > 0 and verified_docs == total_docs
        
        return Response({
            'documents': {
                'total': total_docs,
                'verified': verified_docs,
                'uploaded_types': uploaded_doc_types,
                'missing_types': missing_docs,
                'all_verified': all_docs_verified
            },
            'images': {
                'total': total_images,
                'uploaded_types': uploaded_image_types,
                'missing_types': missing_images
            },
            'ready_for_review': all_required_uploaded,
            'documents_list': DriverVerificationDocumentSerializer(
                documents,
                many=True,
                context={'request': request}
            ).data,
            'images_list': VehicleImageSerializer(
                images,
                many=True,
                context={'request': request}
            ).data
        }, status=status.HTTP_200_OK)
    except Driver.DoesNotExist:
        return Response(
            {'error': 'You do not have a driver profile.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_driver_availability(request):
    """Toggle driver online/offline status"""
    # Apply throttling manually
    throttle = DriverStatusChangeThrottle()
    if not throttle.allow_request(request, None):
        from rest_framework.exceptions import Throttled
        raise Throttled(wait=throttle.wait())  # Throttle: 20 changes/hour
    
    try:
        driver = request.user.driver_profile
        
        if not driver.can_accept_rides:
            return Response(
                {
                    'error': 'You cannot go online.',
                    'reasons': []
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        action = request.data.get('action')  # 'online' or 'offline'
        
        if action == 'online':
            success = driver.go_online()
            if success:
                return Response({
                    'message': 'You are now online and available for rides',
                    'is_online': True,
                    'is_available': True
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Unable to go online. Please check your account status.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        elif action == 'offline':
            driver.go_offline()
            return Response({
                'message': 'You are now offline',
                'is_online': False,
                'is_available': False
            }, status=status.HTTP_200_OK)
        
        else:
            return Response(
                {'error': 'Invalid action. Use "online" or "offline"'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Driver.DoesNotExist:
        return Response(
            {'error': 'You do not have a driver profile.'},
            status=status.HTTP_404_NOT_FOUND
        )

"""
ADD THIS TO drivers/views.py (after toggle_driver_availability)

Endpoint for drivers to update their location in real-time.
"""


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_driver_location(request):
    """
    Update driver's current location.
    Called every 10-30 seconds by driver app while online.
    """
    try:
        driver = request.user.driver_profile
        
        if not driver.is_online:
            return Response(
                {'error': 'You must be online to update location'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude is None or longitude is None:
            return Response(
                {'error': 'latitude and longitude are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate coordinates
        try:
            lat = float(latitude)
            lng = float(longitude)
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError('Invalid coordinate range')
        except ValueError as e:
            return Response(
                {'error': f'Invalid coordinates: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update location using the model's method
        location = driver.update_location(
            latitude=latitude,
            longitude=longitude,
            heading=request.data.get('heading'),
            speed=request.data.get('speed'),
            accuracy=request.data.get('accuracy')
        )
        
        return Response({
            'message': 'Location updated successfully',
            'location': {
                'latitude': float(location.latitude),
                'longitude': float(location.longitude),
                'bearing': float(location.bearing) if location.bearing else None,  # ✅ Correct
                'speed_kmh': float(location.speed_kmh) if location.speed_kmh else None,  # ✅ Correct
                'last_updated': location.last_updated.isoformat()  # ✅ Correct
            }
        }, status=status.HTTP_200_OK)
        
    except Driver.DoesNotExist:
        return Response(
            {'error': 'You do not have a driver profile'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error updating driver location: {str(e)}")
        return Response(
            {'error': f'Failed to update location: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_driver_location(request):
    """Get current driver's own location"""
    try:
        driver = request.user.driver_profile
        
        if not hasattr(driver, 'current_location'):
            return Response(
                {'error': 'No location data available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        location = driver.current_location  # ✅ Fixed
        
        return Response({
            'latitude': float(location.latitude),
            'longitude': float(location.longitude),
            'bearing': float(location.bearing) if location.bearing else None,  # ✅ Fixed
            'speed_kmh': float(location.speed_kmh) if location.speed_kmh else None,  # ✅ Fixed
            'accuracy_meters': float(location.accuracy_meters) if location.accuracy_meters else None,  # ✅ Fixed
            'last_updated': location.last_updated.isoformat(),  # ✅ Fixed
            'is_stale': location.is_stale
        }, status=status.HTTP_200_OK)
        
    except Driver.DoesNotExist:
        return Response(
            {'error': 'You do not have a driver profile'},
            status=status.HTTP_404_NOT_FOUND
        )
# ==================== ADMIN VIEWS ====================

class AdminDriverListView(generics.ListAPIView):
    """Admin: List all driver applications"""
    serializer_class = AdminDriverApprovalSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        status_filter = self.request.query_params.get('status')
        queryset = Driver.objects.select_related('user').prefetch_related(
            'verification_documents', 'vehicle_images'
        )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


class AdminApproveDriverView(generics.UpdateAPIView):
    """Admin: Approve driver application"""
    serializer_class = AdminDriverApprovalSerializer
    permission_classes = [IsAdminUser]
    queryset = Driver.objects.all()
    
    def update(self, request, *args, **kwargs):
        driver = self.get_object()
        
        if driver.status != 'pending':
            return Response(
                {'error': f'Cannot approve. Driver status is "{driver.get_status_display()}".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if all required documents are verified
        required_docs = ['license', 'registration', 'insurance', 'id_card']
        uploaded_docs = driver.verification_documents.values_list('document_type', flat=True)
        verified_docs = driver.verification_documents.filter(is_verified=True).values_list('document_type', flat=True)
        
        missing_docs = [doc for doc in required_docs if doc not in uploaded_docs]
        unverified_docs = [doc for doc in required_docs if doc not in verified_docs]
        
        if missing_docs:
            return Response(
                {
                    'error': 'Cannot approve. Missing required documents.',
                    'missing_documents': missing_docs
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if unverified_docs:
            return Response(
                {
                    'error': 'Cannot approve. Not all documents are verified.',
                    'unverified_documents': unverified_docs
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if background check passed
        if not driver.background_check_passed:
            return Response(
                {'error': 'Cannot approve. Background check has not passed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve driver
        try:
            with transaction.atomic():
                driver.status = 'approved'
                driver.approved_by = request.user
                driver.approved_date = timezone.now()
                driver.save()
                
                # Update user's is_driver flag
                driver.user.is_driver = True
                driver.user.save(update_fields=['is_driver'])
                
                # Audit logging
                logger.info(
                    f"AUDIT: Driver approved | Admin: {request.user.phone_number} | "
                    f"Driver: {driver.user.phone_number} (ID: {driver.id}) | "
                    f"License: {driver.driver_license_number}"
                )
            
            return Response(
                {
                    'message': 'Driver approved successfully',
                    'driver': AdminDriverApprovalSerializer(
                        driver, 
                        context={'request': request}
                    ).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to approve driver: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminRejectDriverView(generics.UpdateAPIView):
    """Admin: Reject driver application"""
    serializer_class = AdminDriverApprovalSerializer
    permission_classes = [IsAdminUser]
    queryset = Driver.objects.all()
    
    def update(self, request, *args, **kwargs):
        driver = self.get_object()
        rejection_reason = request.data.get('rejection_reason')
        
        if not rejection_reason:
            return Response(
                {'error': 'rejection_reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if driver.status != 'pending':
            return Response(
                {'error': f'Cannot reject. Driver status is "{driver.get_status_display()}".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                driver.status = 'rejected'
                driver.rejection_reason = rejection_reason
                driver.approved_by = request.user
                driver.approved_date = timezone.now()
                driver.save()
                
                # Audit logging
                logger.warning(
                    f"AUDIT: Driver rejected | Admin: {request.user.phone_number} | "
                    f"Driver: {driver.user.phone_number} (ID: {driver.id}) | "
                    f"Reason: {rejection_reason[:100]}"
                )
            
            return Response(
                {
                    'message': 'Driver application rejected',
                    'driver': AdminDriverApprovalSerializer(
                        driver, 
                        context={'request': request}
                    ).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to reject driver: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class AdminVerifyDocumentView(generics.UpdateAPIView):
    """Admin: Verify individual driver document"""
    permission_classes = [IsAdminUser]
    queryset = DriverVerificationDocument.objects.all()
    
    def update(self, request, *args, **kwargs):
        doc = self.get_object()
        
        try:
            with transaction.atomic():
                doc.is_verified = True
                doc.verified_by = request.user
                doc.verified_date = timezone.now()
                doc.notes = request.data.get('notes', '')
                doc.save()
                
                # Audit logging
                logger.info(
                    f"AUDIT: Document verified | Admin: {request.user.phone_number} | "
                    f"Driver: {doc.driver.user.phone_number} (ID: {doc.driver.id}) | "
                    f"Document Type: {doc.get_document_type_display()}"
                )
            
            return Response(
                {
                    'message': 'Document verified successfully',
                    'document': DriverVerificationDocumentSerializer(
                        doc, 
                        context={'request': request}
                    ).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to verify document: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_run_background_check(request, pk):
    """Admin: Mark background check as passed/failed"""
    try:
        driver = Driver.objects.get(pk=pk)
        passed = request.data.get('passed', False)
        notes = request.data.get('notes', '')
        
        driver.background_check_passed = passed
        driver.background_check_date = timezone.now()
        driver.background_check_notes = notes
        driver.save()
        
        # Audit logging
        logger.info(
            f"AUDIT: Background check {"passed" if passed else "failed"} | "
            f"Admin: {request.user.phone_number} | "
            f"Driver: {driver.user.phone_number} (ID: {driver.id}) | "
            f"Notes: {notes[:100] if notes else "None"}"
        )
        
        return Response({
            'message': f'Background check marked as {"passed" if passed else "failed"}',
            'driver': AdminDriverApprovalSerializer(driver, context={'request': request}).data
        }, status=status.HTTP_200_OK)
    
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Driver not found'},
            status=status.HTTP_404_NOT_FOUND
        )