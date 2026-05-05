import importlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.apps import apps

from tests.invoices_tests.factories import InvoiceFactory

_migration = importlib.import_module(
    "grandchallenge.invoices.migrations.0012_migrate_invoice_expires_on"
)


@pytest.mark.django_db
def test_set_expires_on_migration(settings):
    # Arrange: Create an invoice with a specific created datetime
    fixed_time = datetime(2025, 1, 29, 11, 0, 0, tzinfo=ZoneInfo("UTC"))

    invoice = InvoiceFactory(
        expires_on=fixed_time.date(),
    )
    invoice.created = fixed_time  # Override the created time to a fixed value
    invoice.save()

    assert (
        invoice.created.date() == invoice.expires_on == fixed_time.date()
    ), "Sanity check before migration"

    # Act: Run the migration
    _migration.set_expires_on(apps, schema_editor=None)

    # Assert: Verify expires_on is set correctly
    invoice.refresh_from_db()

    assert invoice.expires_on == fixed_time.date() + timedelta(
        days=365 * settings.CHALLENGE_INVOICES_DEFAULT_EXPIRE_AFTER_YEARS
    )
