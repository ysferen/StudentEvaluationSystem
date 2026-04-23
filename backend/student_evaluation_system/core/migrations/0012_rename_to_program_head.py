from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_alter_instructorpermission_department_head"),
        ("users", "0006_rename_to_program_head"),
    ]

    operations = [
        migrations.RenameField(
            model_name="instructorpermission",
            old_name="department_head",
            new_name="program_head",
        ),
        migrations.AlterField(
            model_name="instructorpermission",
            name="program_head",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="granted_permissions",
                to="users.programheadprofile",
            ),
        ),
    ]