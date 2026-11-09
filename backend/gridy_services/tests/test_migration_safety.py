from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HistoricalReceiptMigrationTests(TransactionTestCase):
    migrate_from = ("gridy_services", "0020_documentcertificateverification")
    migrate_to = (
        "gridy_services",
        "0021_documentrequest_submission_fingerprint_and_more",
    )

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_duplicate_legacy_receipts_do_not_block_ticket_schema_migration(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Barangay = old_apps.get_model("gridy_auth", "Barangay")
        DocumentRequest = old_apps.get_model("gridy_services", "DocumentRequest")

        barangay = Barangay.objects.create(name="Legacy Receipt Migration Barangay")
        request_fields = {
            "barangay": barangay,
            "document_type": "Barangay Clearance",
            "is_walkin": True,
        }
        first = DocumentRequest.objects.create(
            **request_fields,
            walkin_name="Legacy Resident One",
            or_number="123",
        )
        second = DocumentRequest.objects.create(
            **request_fields,
            walkin_name="Legacy Resident Two",
            or_number=" 123 ",
        )

        MigrationExecutor(connection).migrate([self.migrate_to])

        new_apps = MigrationExecutor(connection).loader.project_state(
            [self.migrate_to]
        ).apps
        QueueTicket = new_apps.get_model("gridy_services", "QueueTicket")
        DocumentRequest = new_apps.get_model("gridy_services", "DocumentRequest")

        self.assertIn("ticket_day", {field.name for field in QueueTicket._meta.fields})
        stored_receipts = list(
            DocumentRequest.objects.filter(pk__in=[first.pk, second.pk])
            .order_by("pk")
            .values_list("or_number", flat=True)
        )
        self.assertEqual(stored_receipts, ["123", " 123 "])
