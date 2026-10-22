from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gridy_auth", "0024_resident_address_details"),
    ]

    operations = [
        migrations.AlterField(
            model_name="privatemediacleanup",
            name="field_name",
            field=models.CharField(
                choices=[
                    ("philsys_id_photo", "PhilSys ID photo"),
                    ("secondary_id_photo", "Secondary ID photo"),
                    ("utility_billing_photo", "Utility billing photo"),
                    ("proof_of_authority", "Barangay authority proof"),
                    ("profile_picture", "Account profile picture"),
                ],
                max_length=32,
            ),
        ),
    ]
