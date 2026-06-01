from django.core.management.base import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.tasks import update_challenge_compute_costs
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


class ChallengeInvoiceRouter:
    def __init__(self):
        # Final update of compute costs to ensure we have the latest information on the invoices
        # before we start routing utilizations to them.
        update_challenge_compute_costs()

        # Preload invoices for all challenges to avoid hitting the database for each challenge.
        # Only select authorized budget; explicitly not filtered on invoices with a positive balance
        # as we'll overcharge the last invoice if we run out of budget, but at least we'll link to an invoice.
        invoices = (
            Invoice.objects.with_budget_authorization()
            .exclude(is_budget_authorized=False)
            .order_by("expires_on", "created")
            .select_related("challenge")
        )

        self.__challenge_to_authorized_invoices = {}
        for invoice in invoices:
            if (
                invoice.challenge_id
                not in self.__challenge_to_authorized_invoices
            ):
                self.__challenge_to_authorized_invoices[
                    invoice.challenge_id
                ] = []
            self.__challenge_to_authorized_invoices[
                invoice.challenge_id
            ].append(invoice)

    def route(self, *, utilization):
        challenge_id = utilization.challenge_id

        try:
            authorized_invoices = self.__challenge_to_authorized_invoices[
                challenge_id
            ]
        except KeyError:
            raise NoAuthorizedInvoiceError

        invoice = self.__select_invoice(
            utilization=utilization, invoices=authorized_invoices
        )
        invoice.compute_cost_euro_millicents += (
            utilization.compute_cost_euro_millicents or 0
        )
        utilization.invoice = invoice

    def __select_invoice(self, *, utilization, invoices):
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


class Command(BaseCommand):
    help = "Routes challenge utilizations to invoices"

    def handle(self, *_, **__):

        utilization_router = ChallengeInvoiceRouter()
        missing_invoice_challenges = set()

        for model in CHALLENGE_UTILIZATION_MODELS:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Progress: started working on {model.__name__}"
                )
            )

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

            queryset = model.objects.filter(
                invoice__isnull=True,
                challenge__isnull=False,
            ).order_by("created")

            # Iterate over the queryset and push bulk updates in batches to avoid overloading the memory
            # at the Python and the database level, respectively.
            objects_to_update = []
            for utilization in queryset.iterator(chunk_size=ITER_BATCH_SIZE):
                try:
                    utilization_router.route(utilization=utilization)
                except NoAuthorizedInvoiceError:
                    missing_invoice_challenges.add(utilization.challenge_id)

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
