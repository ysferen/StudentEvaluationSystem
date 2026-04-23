from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0010_instructor_permission"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instructorpermission",
            name="department_head",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name="granted_permissions",
                to="users.departmentheadprofile",
            ),
        ),
    ]