# Generated manually to preserve existing application rows.

import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gridy_auth", "0018_alter_user_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="barangayapplication",
            name="admin_username",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="barangayapplication",
            name="applicant_authorized",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="barangayapplication",
            name="contact_consent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="barangayapplication",
            name="review_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="barangayapplication",
            name="created_admin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="first_admin_onboarding_applications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="barangayapplication",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("admin_username"),
                condition=models.Q(
                    ("status", "PENDING"),
                    models.Q(("admin_username", ""), _negated=True),
                ),
                name="unique_pending_admin_username",
            ),
        ),
        migrations.AddConstraint(
            model_name="barangayapplication",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("applicant_email"),
                condition=models.Q(
                    ("status", "PENDING"),
                    models.Q(("admin_username", ""), _negated=True),
                ),
                name="unique_pending_admin_email",
            ),
        ),
    ]
