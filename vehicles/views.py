from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Vehicle, VehicleDocument, VehicleImage
from .serializers import (
    VehicleSerializer, VehicleCreateSerializer, VehicleListSerializer,
    VehicleDocumentSerializer, VehicleImageSerializer
)

class VehicleListCreateView(generics.ListCreateAPIView):
    """List and create vehicles for current driver"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VehicleCreateSerializer
        return VehicleListSerializer
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'driver_profile'):
            return Vehicle.objects.none()
        return Vehicle.objects.filter(
            driver=self.request.user.driver_profile
        )
    
    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'driver_profile'):
            raise PermissionDenied('Only drivers can add vehicles')
        serializer.save(driver=self.request.user.driver_profile)


class VehicleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or deactivate vehicle"""
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not hasattr(self.request.user, 'driver_profile'):
            return Vehicle.objects.none()
        return Vehicle.objects.filter(
            driver=self.request.user.driver_profile
        )
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_primary_vehicle(request, vehicle_id):
    """Set vehicle as primary"""
    try:
        driver = request.user.driver_profile
        vehicle = Vehicle.objects.get(id=vehicle_id, driver=driver)
        
        # Unset other primary vehicles
        Vehicle.objects.filter(driver=driver).update(is_primary=False)
        
        # Set this as primary
        vehicle.is_primary = True
        vehicle.save()
        
        return Response({
            'success': True,
            'message': 'Primary vehicle updated',
            'vehicle': VehicleSerializer(vehicle).data
        })
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_vehicle_document(request, vehicle_id):
    """Upload vehicle document"""
    try:
        driver = request.user.driver_profile
        vehicle = Vehicle.objects.get(id=vehicle_id, driver=driver)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=404)
    
    document_type = request.data.get('document_type')
    document_file = request.FILES.get('document')
    
    if not document_type or not document_file:
        return Response({
            'error': 'document_type and document file required'
        }, status=400)
    
    # Delete existing document of same type
    VehicleDocument.objects.filter(
        vehicle=vehicle,
        document_type=document_type
    ).delete()
    
    # Create new document
    doc = VehicleDocument.objects.create(
        vehicle=vehicle,
        document_type=document_type,
        document=document_file,
        expiry_date=request.data.get('expiry_date')
    )
    
    return Response(
        VehicleDocumentSerializer(doc, context={'request': request}).data,
        status=201
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_vehicle_image(request, vehicle_id):
    """Upload vehicle image"""
    try:
        driver = request.user.driver_profile
        vehicle = Vehicle.objects.get(id=vehicle_id, driver=driver)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=404)
    
    image_type = request.data.get('image_type')
    image_file = request.FILES.get('image')
    
    if not image_type or not image_file:
        return Response({
            'error': 'image_type and image file required'
        }, status=400)
    
    # Delete existing image of same type
    VehicleImage.objects.filter(
        vehicle=vehicle,
        image_type=image_type
    ).delete()
    
    # Create new image
    img = VehicleImage.objects.create(
        vehicle=vehicle,
        image_type=image_type,
        image=image_file
    )
    
    return Response(
        VehicleImageSerializer(img, context={'request': request}).data,
        status=201
    )
    

"""
ADD THIS TO vehicles/views.py (at the end)

Endpoint to check vehicle roadworthiness and expiry warnings.
"""

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_vehicle_status(request, vehicle_id):
    """
    Check vehicle roadworthiness status and get warnings.
    
    Returns:
    - is_roadworthy: bool
    - issues: list of problems preventing rides
    - warnings: list of upcoming expirations
    - health_score: 0-100
    - documents_complete: bool
    - images_complete: bool
    """
    try:
        driver = request.user.driver_profile
        vehicle = Vehicle.objects.get(id=vehicle_id, driver=driver)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=404)
    
    from .utils import (
        validate_vehicle_roadworthiness,
        calculate_vehicle_health_score,
        get_vehicle_expiry_warnings,
        check_vehicle_documents_complete,
        check_vehicle_images_complete
    )
    
    # Check roadworthiness
    is_roadworthy, issues = validate_vehicle_roadworthiness(vehicle)
    
    # Get expiry warnings
    warnings = get_vehicle_expiry_warnings(vehicle)
    
    # Calculate health score
    health_score = calculate_vehicle_health_score(vehicle)
    
    # Check document/image completeness
    docs_complete, missing_docs = check_vehicle_documents_complete(vehicle)
    images_complete, missing_images = check_vehicle_images_complete(vehicle)
    
    return Response({
        'vehicle': VehicleSerializer(vehicle, context={'request': request}).data,
        'is_roadworthy': is_roadworthy,
        'issues': issues,
        'warnings': warnings,
        'health_score': health_score,
        'documents': {
            'complete': docs_complete,
            'missing': missing_docs,
            'uploaded': list(vehicle.documents.values_list('document_type', flat=True))
        },
        'images': {
            'complete': images_complete,
            'missing': missing_images,
            'uploaded': list(vehicle.images.values_list('image_type', flat=True))
        },
        'can_accept_rides': is_roadworthy
    })

