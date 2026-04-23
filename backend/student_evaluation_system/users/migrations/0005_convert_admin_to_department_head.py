from django.db import migrations


def convert_admins_with_departments(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    DepartmentHeadProfile = apps.get_model("users", "DepartmentHeadProfile")
    for user in CustomUser.objects.filter(role="admin", department__isnull=False):
        user.role = "department_head"
        user.save(update_fields=["role"])
        if not hasattr(user, "department_head_profile"):
            DepartmentHeadProfile.objects.create(
                user=user,
                department=user.department,
            )


def reverse_convert(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    DepartmentHeadProfile = apps.get_model("users", "DepartmentHeadProfile")
    for profile in DepartmentHeadProfile.objects.all():
        profile.user.role = "admin"
        profile.user.save(update_fields=["role"])
    DepartmentHeadProfile.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_department_head_profile"),
    ]

    operations = [
        migrations.RunPython(convert_admins_with_departments, reverse_convert),
    ]
