import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def convert_department_head_to_program_head(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.filter(role="department_head").update(role="program_head")


def reverse_convert(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    CustomUser.objects.filter(role="program_head").update(role="department_head")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_alter_instructorpermission_department_head"),
        ("users", "0005_convert_admin_to_department_head"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="DepartmentHeadProfile",
            new_name="ProgramHeadProfile",
        ),
        migrations.RenameField(
            model_name="programheadprofile",
            old_name="department",
            new_name="program",
        ),
        migrations.AlterField(
            model_name="customuser",
            name="role",
            field=models.CharField(
                choices=[
                    ("guest", "Guest"),
                    ("student", "Student"),
                    ("instructor", "Instructor"),
                    ("program_head", "Program Head"),
                    ("admin", "Admin"),
                ],
                default="guest",
                max_length=15,
            ),
        ),
        migrations.RunPython(
            convert_department_head_to_program_head,
            reverse_convert,
        ),
    ]