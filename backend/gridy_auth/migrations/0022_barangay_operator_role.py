from django.db import migrations, models


def rename_dilg_operator_role(apps, schema_editor):
    User = apps.get_model("gridy_auth", "User")
    User.objects.filter(role="DILG_ADMIN").update(role="BARANGAY_OPERATOR")


def restore_dilg_operator_role(apps, schema_editor):
    User = apps.get_model("gridy_auth", "User")
    User.objects.filter(role="BARANGAY_OPERATOR").update(role="DILG_ADMIN")


class Migration(migrations.Migration):
    dependencies = [
        ("gridy_auth", "0021_barangayapplication_email_verification_sent_at_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_dilg_operator_role, restore_dilg_operator_role),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Admin"),
                    ("RESIDENT", "Resident"),
                    ("FIELD_OFFICIAL", "Field Official"),
                    ("BARANGAY_OPERATOR", "Barangay Operator"),
                ],
                default="RESIDENT",
                max_length=50,
            ),
        ),
    ]
