from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gridy_services', '0017_merge_20261014_1559'),
    ]

    operations = [
        migrations.AddField(
            model_name='queueticket',
            name='document_request',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='queue_tickets',
                to='gridy_services.documentrequest',
            ),
        ),
        migrations.AddConstraint(
            model_name='queueticket',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('document_request__isnull', False),
                    ('status__in', ['WAITING', 'SERVING']),
                ),
                fields=('document_request',),
                name='one_active_queue_ticket_per_document_request',
            ),
        ),
    ]
