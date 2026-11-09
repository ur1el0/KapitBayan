from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gridy_auth", "0027_resident_guardianship_review"),
        ("gridy_services", "0021_documentrequest_submission_fingerprint_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentrequest",
            name="or_number",
            field=models.CharField(
                blank=True,
                help_text="Barangay-approved O.R. number assigned from the configured series after payment confirmation.",
                max_length=50,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="OfficialReceiptSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prefix", models.CharField(max_length=40)),
                ("next_number", models.PositiveBigIntegerField()),
                ("number_width", models.PositiveSmallIntegerField(default=0, help_text="Minimum serial width; zero disables leading zero padding.")),
                ("last_issued_number", models.PositiveBigIntegerField(blank=True, editable=False, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("barangay", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="official_receipt_series", to="gridy_auth.barangay")),
            ],
        ),
    ]
