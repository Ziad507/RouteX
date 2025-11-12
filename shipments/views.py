from rest_framework import generics, status, serializers
from django.db.models import Count, ProtectedError, OuterRef, Subquery, Case, When, Value, BooleanField, F, Q
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils.dateparse import parse_datetime
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from .permissions import IsWarehouseManager, IsDriver
from .models import Shipment, StatusUpdate, WarehouseManager, Customer, Warehouse, Driver, Product
from .serializers import (
    StatusUpdateSerializer, ShipmentSerializer,
    CustomerSerializer, WarehouseSerializer, DriverStatusSerializer, ProductSerializer
)
from .constants import SHIPMENT_LIST_LIMIT, AUTOCOMPLETE_LIMIT, ACTIVE_STATUSES
from .mixins import WarehouseManagerQuerysetMixin


# 1) product list/create (warehouse manager only)
@extend_schema(tags=["Products"])
class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsWarehouseManager]
    queryset = Product.objects.all().annotate(shipments_count=Count('shipments'))
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        """List products with caching."""
        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Create product and invalidate cache."""
        response = super().create(request, *args, **kwargs)
        # Invalidate product list cache
        try:
            # Try to delete cache keys (may fail if cache doesn't support keys())
            if hasattr(cache, 'keys'):
                keys = cache.keys("products_list_*")
                if keys:
                    cache.delete_many(keys)
        except (AttributeError, NotImplementedError):
            pass
        cache.delete("products_list")
        return response


# 2) product detail/update/delete (warehouse manager only)
@extend_schema(tags=["Products"])
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsWarehouseManager]
    queryset = Product.objects.all().annotate(shipments_count=Count('shipments'))
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {
                    "detail": "Cannot delete the product because there are shipments linked to it.",
                    "shipments_count": getattr(instance, "shipments_count", None),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# 3) Shipment create (warehouse manager only)
@extend_schema(tags=["Shipments"])
class ShipmentCreateView(generics.CreateAPIView):
    queryset = Shipment.objects.select_related("product", "warehouse", "driver__user", "customer")
    serializer_class = ShipmentSerializer
    permission_classes = [IsWarehouseManager]


# 4) detail/update/delete shipment (warehouse manager only)
@extend_schema(tags=["Shipments"])
class ShipmentDetailView(WarehouseManagerQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Shipment.objects.select_related("product", "warehouse", "driver__user", "customer")
    serializer_class = ShipmentSerializer
    permission_classes = [IsWarehouseManager]

    @transaction.atomic
    def perform_destroy(self, instance: Shipment):
        # Release stock when deleting a shipment with assigned driver and product
        if instance.driver_id and instance.product_id:
            quantity = getattr(instance, "quantity", 1)
            Product.objects.filter(pk=instance.product_id).update(
                stock_qty=F("stock_qty") + quantity
            )
        
        # Invalidate caches
        cache.delete("products_list")
        if instance.product_id:
            cache.delete(f"product_{instance.product_id}")
        cache.delete("drivers_list")
        if instance.driver_id:
            try:
                driver = Driver.objects.get(pk=instance.driver_id)
                cache.delete(f"driver_status_{driver.user.id}")
            except Driver.DoesNotExist:
                pass
        
        super().perform_destroy(instance)


# 5) shipments list (warehouse manager only)
@extend_schema(tags=["Shipments"])
class ShipmentsListView(WarehouseManagerQuerysetMixin, generics.ListAPIView):
    permission_classes = [IsWarehouseManager]
    serializer_class = ShipmentSerializer

    def get_queryset(self):
        qs = Shipment.objects.select_related("product", "warehouse", "driver__user", "customer")
        updated_since = self.request.query_params.get("updated_since")
        if updated_since:
            dt = parse_datetime(updated_since)
            if dt:
                qs = qs.filter(updated_at__gte=dt)
        return qs.order_by("-updated_at")[:SHIPMENT_LIST_LIMIT]


# 6) Autocomplete shipments (warehouse manager only)
@extend_schema(tags=["Autocomplete"])
class AutocompleteShipmentsView(WarehouseManagerQuerysetMixin, generics.ListAPIView):
    serializer_class = ShipmentSerializer
    permission_classes = [IsWarehouseManager]

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()
        qs = Shipment.objects.select_related("product", "customer", "driver__user", "warehouse")
        if q:
            if q.isdigit():
                qs = qs.filter(id=int(q))
            else:
                qs = qs.filter(
                    Q(product__name__icontains=q) |  # Search by product name
                    Q(notes__icontains=q)
                )
        return qs.order_by("-updated_at")[:AUTOCOMPLETE_LIMIT]


# 7) warehouse create (warehouse manager only)
@extend_schema(tags=["Warehouses"])
class WarehouseListCreateView(generics.ListCreateAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseManager]


# 8) detail/update/delete warehouse (warehouse manager only)
@extend_schema(tags=["Warehouses"])
class WarehouseDetailView(WarehouseManagerQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WarehouseSerializer
    permission_classes = [IsWarehouseManager]
    queryset = Warehouse.objects.all()


# 9) customer create (warehouse manager only)
@extend_schema(tags=["Customers"])
class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsWarehouseManager]


# 10) detail/update/delete customer (warehouse manager only)
@extend_schema(tags=["Customers"])
class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsWarehouseManager]


# 11) customer addresses list (warehouse manager only)
class CustomerAddressesView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    permission_classes = [IsWarehouseManager]

    # Minimal serializer so DRF/drf-spectacular can introspect the response
    class CustomerAddressesResponseSerializer(serializers.Serializer):
        customer_id = serializers.IntegerField()
        addresses = serializers.ListField(child=serializers.CharField())

    serializer_class = CustomerAddressesResponseSerializer

    @extend_schema(
        tags=["Customers"],
        responses={
            200: OpenApiResponse(
                description="Customer addresses list",
                response=inline_serializer(
                    name="CustomerAddressesResponse",
                    fields={
                        "customer_id": serializers.IntegerField(),
                        "addresses": serializers.ListSerializer(child=serializers.CharField()),
                    },
                ),
            ),
            404: OpenApiResponse(description="Customer not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        customer = self.get_object()
        addresses = [a for a in (customer.address, customer.address2, customer.address3) if a]
        return Response({
            "customer_id": customer.id,
            "addresses": addresses
        })


# 12) Autocomplete customers (warehouse manager only)
@extend_schema(tags=["Autocomplete"])
class AutocompleteCustomersView(WarehouseManagerQuerysetMixin, generics.ListAPIView):
    """
    Query parameter: q
    - q isdigit => match ID/phone
    - q text => match name/phone
    """
    serializer_class = CustomerSerializer
    permission_classes = [IsWarehouseManager]

    def get_queryset(self):
        q = (self.request.query_params.get("q") or "").strip()

        qs = Customer.objects.all()

        if q:
            if q.isdigit():
                qs = qs.filter(Q(id=int(q)) | Q(phone__icontains=q))
            else:
                qs = qs.filter(
                    Q(name__icontains=q) |
                    Q(phone__icontains=q)
                )

        return qs.order_by("-updated_at")[:AUTOCOMPLETE_LIMIT]

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        # fields to keep in this endpoint
        keep = {"id", "name", "phone", "address"}

        if isinstance(serializer, drf_serializers.ListSerializer):
            fields = serializer.child.fields
        else:
            fields = serializer.fields

        for name in list(fields):
            if name not in keep:
                fields.pop(name)

        return serializer


# 13) driver status list (warehouse manager only)
@extend_schema(tags=["Drivers"])
class DriverStatusView(viewsets.ReadOnlyModelViewSet):
    serializer_class = DriverStatusSerializer
    permission_classes = [IsWarehouseManager]
    # filter_backends   = [filters.SearchFilter]
    search_fields = ["user__username", "user__phone"]

    @method_decorator(cache_page(60 * 2))  # Cache for 2 minutes (driver status changes frequently)
    def list(self, request, *args, **kwargs):
        """List drivers with caching."""
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        latest_update_qs = (
            StatusUpdate.objects
            .filter(shipment__driver=OuterRef("pk"))
            .order_by("-timestamp")
        )

        active_shipment_qs = (
            Shipment.objects
            .filter(driver=OuterRef("pk"))
            .annotate(
                _last_status=Subquery(
                    StatusUpdate.objects
                    .filter(shipment=OuterRef("pk"))
                    .order_by("-timestamp")
                    .values("status")[:1]
                )
            )
            .filter(_last_status__in=ACTIVE_STATUSES)
            .order_by("-updated_at")
            .values("id")[:1]
        )

        qs = (
            Driver.objects.select_related("user")
            .annotate(
                last_status=Subquery(latest_update_qs.values("status")[:1]),
                last_seen_at=Subquery(latest_update_qs.values("timestamp")[:1]),
                current_active_shipment_id=Subquery(active_shipment_qs),
            )
            .annotate(
                effective_is_active=Case(
                    When(last_status="DELIVERED", then=Value(True)),
                    default=F("is_active"),
                    output_field=BooleanField(),
                )
            )
            .order_by("user__username", "pk")
        )
        return qs


@extend_schema(
    tags=["Drivers"],
    summary="عرض تفاصيل سائق محدد",
    description="يعرض بيانات السائق (الحالة، المستخدم المرتبط). يتطلب صلاحيات مدير مستودع.",
    responses={
        200: OpenApiResponse(
            description="تفاصيل السائق",
            response=inline_serializer(
                name="DriverDetailResponse",
                fields={
                    "id": serializers.IntegerField(),
                    "user_id": serializers.IntegerField(),
                    "username": serializers.CharField(),
                    "phone": serializers.CharField(),
                    "is_active": serializers.BooleanField(),
                    "status": serializers.CharField(help_text="available or busy"),
                },
            ),
        ),
        404: OpenApiResponse(description="السائق غير موجود"),
    },
)
class DriverDetailManagerView(APIView):
    """
    GET: عرض حالة السائق وبياناته باستخدام معرّف السائق.
    DELETE: حذف السائق (والحساب المرتبط) نهائياً.
    """
    permission_classes = [IsWarehouseManager]

    def _get_driver(self, pk: int) -> Driver:
        return Driver.objects.select_related("user").get(pk=pk)

    def get(self, request, pk: int):
        try:
            driver = self._get_driver(pk)
        except Driver.DoesNotExist:
            return Response({"detail": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)

        status_text = "available" if driver.is_active else "busy"
        from users.utils import mask_phone
        
        return Response({
            "id": driver.id,
            "user_id": driver.user.id,
            "username": driver.user.username,
            "phone": mask_phone(driver.user.phone),  # Masked for privacy
            "is_active": driver.is_active,
            "status": status_text,
        })

    @extend_schema(
        tags=["Drivers"],
        summary="حذف سائق",
        description="يحذف السائق والحساب المرتبط به. هذه العملية لا يمكن التراجع عنها.",
        responses={
            200: OpenApiResponse(description="تم حذف السائق"),
            404: OpenApiResponse(description="السائق غير موجود"),
        },
    )
    def delete(self, request, pk: int):
        try:
            driver = self._get_driver(pk)
        except Driver.DoesNotExist:
            return Response({"detail": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)

        # حذف المستخدم المرتبط سيحذف السائق بسبب العلاقة OneToOne
        user_username = driver.user.username
        driver.user.delete()

        return Response(
            {"detail": f"Driver '{user_username}' deleted successfully."},
            status=status.HTTP_200_OK,
        )


# 14) list shipments assigned to the logged-in driver
@extend_schema(tags=["Driver"])
class DriverShipmentsList(generics.ListAPIView):
    serializer_class = ShipmentSerializer
    permission_classes = [IsDriver]

    def get_queryset(self):
        return (Shipment.objects
                .select_related("product", "driver__user", "warehouse", "customer")
                .filter(driver__user=self.request.user)
                .order_by("-assigned_at"))

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)

        keep = {
            "id",
            "warehouse",
            "product_name",
            "driver_username",
            "customer_name", "customer_address",
            "notes",
            "current_status",
            "created_at", "updated_at",
        }

        if isinstance(serializer, drf_serializers.ListSerializer):
            fields = serializer.child.fields
        else:
            fields = serializer.fields

        for name in list(fields):
            if name not in keep:
                fields.pop(name)

        return serializer


# 15) driver posts a status update for a shipment
@extend_schema(tags=["Driver"])
class StatusUpdateCreateView(generics.CreateAPIView):
    parser_classes = [MultiPartParser, FormParser]
    queryset = StatusUpdate.objects.select_related("shipment", "shipment__driver", "shipment__product")
    serializer_class = StatusUpdateSerializer
    permission_classes = [IsDriver]

    @transaction.atomic
    def perform_create(self, serializer):
        su: StatusUpdate = serializer.save()
        shipment: Shipment = su.shipment

        if shipment.current_status != su.status:
            shipment.current_status = su.status
            shipment.save(update_fields=["current_status", "updated_at"])
