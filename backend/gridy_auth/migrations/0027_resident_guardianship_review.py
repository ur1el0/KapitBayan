# Generated for the minor resident guardianship review flow.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gridy_auth", "0026_loginevent_residenttransferrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="resident",
            name="guardian_relationship",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PARENT", "Parent"),
                    ("COURT_APPOINTED", "Court-appointed guardian"),
                    ("OTHER_AUTHORIZED", "Other authorized guardian"),
                ],
                default="",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="resident",
            name="guardianship_evidence",
            field=models.ImageField(
                blank=True,
                help_text="Private supporting evidence reviewed by the resident's Barangay Admin.",
                null=True,
                upload_to="resident_guardianship/",
            ),
        ),
        migrations.AddField(
            model_name="resident",
            name="guardian_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resident",
            name="guardian_reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_minor_guardianships",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
