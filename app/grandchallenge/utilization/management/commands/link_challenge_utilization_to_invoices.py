from typing import DefaultDict

from django.core.management.base import BaseCommand

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


# TODO: test compute_cost_euro_millicents on util on None
# TODO: test non-challenge linked utilizations
# TODO: sort utilizations on created?

# TODO: call the task that updates utilization prior to this command, to ensure we have the latest compute costs on the invoices.


class InvoiceBooker:
    def __init__(self, *, invoices):
        # Only select authorized budget; explicitly not filtered on invoices with a positive balance
        # as we'll overcharge the last invoice if we run out of budget, but at least we'll link to an invoice.
        self.__authorized_invoices = [
            invoice for invoice in invoices if invoice.is_budget_authorized
        ]

        if not self.__authorized_invoices:
            raise NoAuthorizedInvoiceError

    def book_to_invoice(self, *, utilization):
        invoice = self.__select_invoice(utilization=utilization)
        invoice.compute_cost_euro_millicents += (
            utilization.compute_cost_euro_millicents
        )
        utilization.invoice = invoice

    def __select_invoice(self, *, utilization):
        for invoice in self.__authorized_invoices[:-1]:
            remaining_budget_millicents = (
                invoice.compute_costs_euros * 1000 * 100
                - invoice.compute_cost_euro_millicents
            )

            if (
                remaining_budget_millicents > 0
                and utilization.created <= invoice.expires_on
            ):
                return invoice
        else:
            return self.__authorized_invoices[-1]


class InvoiceBookerManager:
    def __init__(self):
        self.challenge_ids_without_authorized_invoices = set()
        self.__bookers = {}

        # Preload invoices for all challenges to avoid hitting the database for each challenge.
        invoices = Invoice.objects.order_by(
            "expires_on", "created"
        ).select_related("challenge")

        self.__challenge_to_invoices = DefaultDict(list)
        for invoice in invoices:
            self.__challenge_to_invoices[invoice.challenge_id].append(invoice)

    def book_to_invoice(self, *, utilization):
        challenge_id = utilization.challenge_id

        if challenge_id in self.challenge_ids_without_authorized_invoices:
            return  # Short circuit: we know it is hopeless.

        if challenge_id not in self.__bookers:
            invoices = self.__challenge_to_invoices.get(challenge_id, [])
            try:
                self.__bookers[challenge_id] = InvoiceBooker(invoices=invoices)
            except NoAuthorizedInvoiceError:
                self.challenge_ids_without_authorized_invoices.add(
                    challenge_id
                )
                return

        self.__bookers[challenge_id].book_to_invoice(utilization=utilization)


class Command(BaseCommand):
    help = "Links challenge utilizations to invoices"

    def handle(self, *_, **__):

        booker_manager = InvoiceBookerManager()

        for model in CHALLENGE_UTILIZATION_MODELS:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Progress: started working on {model.__name__}"
                )
            )

            queryset = model.objects.filter(
                invoice__isnull=True,
                challenge__isnull=False,
            ).order_by("created")

            updated = 0
            objects_to_update = []

            def push_bulk_update():
                nonlocal updated
                nonlocal objects_to_update
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

            # Iterate over the queryset and push bulk updates in batches to avoid overloading the memory
            # at the Python and the database level, respectively.
            objects_to_update = []
            for utilization in queryset.iterator(chunk_size=ITER_BATCH_SIZE):
                booker_manager.book_to_invoice(utilization=utilization)
                objects_to_update.append(utilization)

                if len(objects_to_update) >= ITER_BATCH_SIZE:
                    push_bulk_update()

            # Handle remaining objects
            if objects_to_update:
                push_bulk_update()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Progress: finished working on {model.__name__}."
                )
            )

        if booker_manager.challenge_ids_without_authorized_invoices:
            challenges = Challenge.objects.filter(
                pk__in=booker_manager.challenge_ids_without_authorized_invoices
            ).values_list("short_name", flat=True)

            self.stdout.write(
                self.style.ERROR(
                    f"Final Report: no authorized invoice found for {len(challenges)} challenges: {', '.join(challenges)}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Final Report: all challenges had an authorized invoice to link to."
                )
            )
