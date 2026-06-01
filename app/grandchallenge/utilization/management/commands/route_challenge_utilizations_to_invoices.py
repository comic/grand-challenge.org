from typing import DefaultDict

from django.core.management.base import BaseCommand
from django.db.models import F

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import Invoice
from grandchallenge.utilization.models import (
    EvaluationUtilization,
    JobUtilization,
    JobWarmPoolUtilization,
)

CHALLENGE_UTILIZATION_MODELS = (
    JobUtilization,
    EvaluationUtilization,
    JobWarmPoolUtilization,
)

ITER_BATCH_SIZE = 10_000
UPDATE_BATCH_SIZE = 1_000


class NoAuthorizedInvoiceError(Exception):
    pass


def get_invoice_map():
    # Only select authorized budget; explicitly not filtered on invoices with a positive balance
    # as we'll overcharge the last invoice if we run out of budget, but at least we'll link to an invoice.

    invoices = DefaultDict(list)

    for invoice in (
        Invoice.objects.with_budget_authorization()
        .exclude(is_budget_authorized=False)
        .order_by("expires_on", "created")
    ):
        invoices[invoice.challenge_id].append(invoice)
        invoice._original_compute_cost_euro_millicents = (
            invoice.compute_cost_euro_millicents
        )

    return invoices


def select_invoice(*, utilization, invoices):
    for invoice in invoices[:-1]:
        remaining_budget_millicents = (
            invoice.compute_costs_euros * 1000 * 100
            - invoice.compute_cost_euro_millicents
        )

        if (
            remaining_budget_millicents > 0
            and utilization.created.date() <= invoice.expires_on
        ):
            return invoice
    else:
        return invoices[-1]


def update_invoice_compute_costs(*, invoices):
    for invoice in invoices:
        diff = (
            invoice.compute_cost_euro_millicents
            - invoice._original_compute_cost_euro_millicents
        )
        # Note: use increment to avoid overwriting concurrent updates
        invoice.compute_cost_euro_millicents = (
            F("compute_cost_euro_millicents") + diff
        )

    Invoice.objects.bulk_update(
        invoices,
        fields=["compute_cost_euro_millicents"],
    )


class Command(BaseCommand):
    help = "Routes challenge utilizations to invoices"

    def handle(self, *_, **__):

        missing_invoice_challenges = set()

        for model in CHALLENGE_UTILIZATION_MODELS:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Progress: started working on {model.__name__}"
                )
            )

            updated = 0
            objects_to_update = []
            invoices_map = get_invoice_map()

            queryset = model.objects.filter(
                invoice__isnull=True,
                challenge__isnull=False,
            ).order_by("created")

            # Iterate over the queryset and push bulk updates in batches to avoid overloading the memory
            # at the Python and the database level, respectively.
            objects_to_update = []
            for utilization in queryset.iterator(chunk_size=ITER_BATCH_SIZE):
                if utilization.challenge_id not in invoices_map:
                    missing_invoice_challenges.add(utilization.challenge_id)
                    continue

                invoice = select_invoice(
                    utilization=utilization,
                    invoices=invoices_map[utilization.challenge_id],
                )
                invoice.compute_cost_euro_millicents += (
                    utilization.compute_cost_euro_millicents or 0
                )
                utilization.invoice = invoice

                objects_to_update.append(utilization)

                if len(objects_to_update) >= ITER_BATCH_SIZE:
                    update_invoice_compute_costs(
                        invoices=(
                            invoice
                            for invoices in invoices_map.values()
                            for invoice in invoices
                        ),
                    )
                    invoices_map = get_invoice_map()

                    updated += model.objects.bulk_update(
                        objs=objects_to_update,
                        fields=["invoice"],
                        batch_size=UPDATE_BATCH_SIZE,
                    )
                    objects_to_update = []
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Progress: {updated} {model.__name__} updated."
                        )
                    )

            # Handle remaining objects
            if objects_to_update:
                update_invoice_compute_costs(
                    invoices=(
                        invoice
                        for invoices in invoices_map.values()
                        for invoice in invoices
                    ),
                )
                model.objects.bulk_update(
                    objs=objects_to_update,
                    fields=["invoice"],
                    batch_size=UPDATE_BATCH_SIZE,
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Progress: finished working on {model.__name__}."
                )
            )

        if missing_invoice_challenges:
            challenges = Challenge.objects.filter(
                pk__in=missing_invoice_challenges
            ).values_list("short_name", flat=True)

            self.stdout.write(
                self.style.ERROR(
                    f"Final Report: no authorized invoice found for "
                    f"{len(challenges)} challenge{'s' if len(challenges) != 1 else ''}: {', '.join(challenges)}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Final Report: all utilizations had an authorized invoice to route to."
                )
            )
