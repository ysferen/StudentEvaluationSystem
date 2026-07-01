from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from core.models import InstructorPermission
from core.serializers import (
    InstructorPermissionSerializer,
    BulkInstructorPermissionSerializer,
    BulkPermissionUpdateSerializer,
)
from core.permissions import IsAdminOrProgramHead


class InstructorPermissionViewSet(viewsets.ModelViewSet):
    queryset = InstructorPermission.objects.select_related(
        "instructor__user", "program_head__user", "program_head__program"
    ).all()
    serializer_class = InstructorPermissionSerializer

    def get_permissions(self):
        if self.action == "my_permissions":
            return [IsAuthenticated()]
        if self.action == "bulk_set":
            return [IsAuthenticated(), IsAdminOrProgramHead()]
        return [IsAuthenticated(), IsAdminOrProgramHead()]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return self.queryset
        if user.is_program_head:
            return self.queryset.filter(instructor__user__department_id=user.department_id)
        if user.is_instructor:
            return self.queryset.filter(instructor__user=user)
        return self.queryset.none()

    @action(detail=False, methods=["get"], url_path="my-permissions")
    def my_permissions(self, request):
        if not request.user.is_instructor:
            return Response(
                {"detail": "Only instructors can view their permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        perms = self.queryset.filter(instructor__user=request.user)
        serializer = self.get_serializer(perms, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=BulkInstructorPermissionSerializer,
        responses={200: InstructorPermissionSerializer(many=True)},
    )
    @action(detail=False, methods=["put"], url_path="bulk")
    def bulk_set(self, request):
        serializer = BulkInstructorPermissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        instructor_id = serializer.validated_data["instructor_id"]
        permissions_data = serializer.validated_data["permissions"]

        from users.models import InstructorProfile

        try:
            instructor = InstructorProfile.objects.get(pk=instructor_id)
        except InstructorProfile.DoesNotExist:
            return Response(
                {"detail": "Instructor not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.is_program_head and instructor.user.department_id != request.user.department_id:
            return Response({"detail": "Instructor is outside your department."}, status=status.HTTP_403_FORBIDDEN)

        if request.user.is_admin_user:
            program_head = None
        else:
            program_head = request.user.program_head_profile

        for perm_data in permissions_data:
            InstructorPermission.objects.update_or_create(
                instructor=instructor,
                resource_area=perm_data["resource_area"],
                defaults={
                    "program_head": program_head,
                    "permission_tier": perm_data["permission_tier"],
                },
            )

        perms = self.queryset.filter(instructor=instructor)
        response_serializer = self.get_serializer(perms, many=True)
        return Response(response_serializer.data)

    @extend_schema(
        request=BulkPermissionUpdateSerializer,
        responses={200: InstructorPermissionSerializer(many=True)},
    )
    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_partial_update(self, request):
        """Bulk partial update - only send changed permissions with their IDs."""
        serializer = BulkPermissionUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updates = serializer.validated_data["updates"]

        # Build a queryset scoped to what the user can update.
        user = request.user
        if user.is_admin_user:
            allowed_qs = InstructorPermission.objects
        elif user.is_program_head:
            allowed_qs = self.queryset.filter(instructor__user__department_id=user.department_id)
        else:
            return Response(
                {"detail": "You do not have permission to update permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update only allowed permissions
        updated_count = 0
        for update_item in updates:
            perm_id = update_item["id"]
            update_fields = {k: v for k, v in update_item.items() if k != "id" and v is not None}
            if update_fields:
                updated_count += allowed_qs.filter(id=perm_id).update(**update_fields)

        # Return all permissions for the program head's scope
        perms = self.queryset
        if not user.is_admin_user:
            perms = perms.filter(program_head__user=user)
        response_serializer = self.get_serializer(perms, many=True)
        return Response(response_serializer.data)
