from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import InstructorPermission
from core.serializers import InstructorPermissionSerializer
from core.permissions import IsAdmin, IsAdminOrDepartmentHead, IsDepartmentHead


class InstructorPermissionViewSet(viewsets.ModelViewSet):
    queryset = InstructorPermission.objects.select_related(
        "instructor__user", "department_head__user", "department_head__department"
    ).all()
    serializer_class = InstructorPermissionSerializer

    def get_permissions(self):
        if self.action == "my_permissions":
            return [IsAuthenticated()]
        if self.action == "bulk_set":
            return [IsAuthenticated(), IsAdminOrDepartmentHead()]
        return [IsAuthenticated(), IsAdminOrDepartmentHead()]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin_user:
            return self.queryset
        if user.is_department_head:
            return self.queryset.filter(
                department_head__user=user
            )
        if user.is_instructor:
            return self.queryset.filter(
                instructor__user=user
            )
        return self.queryset.none()

    @action(detail=False, methods=["get"], url_path="my-permissions")
    def my_permissions(self, request):
        if not request.user.is_instructor:
            return Response(
                {"detail": "Only instructors can view their permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )
        perms = self.queryset.filter(
            instructor__user=request.user
        )
        serializer = self.get_serializer(perms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["put"], url_path="bulk")
    def bulk_set(self, request):
        instructor_id = request.data.get("instructor_id")
        permissions_data = request.data.get("permissions", [])

        if not instructor_id:
            return Response(
                {"detail": "instructor_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from users.models import InstructorProfile

        try:
            instructor = InstructorProfile.objects.get(pk=instructor_id)
        except InstructorProfile.DoesNotExist:
            return Response(
                {"detail": "Instructor not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.is_admin_user:
            department_head = None
        else:
            department_head = request.user.department_head_profile

        for perm_data in permissions_data:
            InstructorPermission.objects.update_or_create(
                instructor=instructor,
                resource_area=perm_data["resource_area"],
                defaults={
                    "department_head": department_head,
                    "permission_tier": perm_data["permission_tier"],
                },
            )

        perms = self.queryset.filter(instructor=instructor)
        serializer = self.get_serializer(perms, many=True)
        return Response(serializer.data)