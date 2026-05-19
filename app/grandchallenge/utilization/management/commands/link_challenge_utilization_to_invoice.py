from django.core.management.base import BaseCommand
from django.db.models import Q

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


class NoInvoiceError(Exception):
    pass


class Command(BaseCommand):
    help = "Links challenge utilizations to invoices"

    def handle(self, *_, **__):
        challenges_with_unlinked_utilization = Challenge.objects.filter(
            Q(job_utilizations__invoice__isnull=True)
            | Q(evaluation_utilizations__invoice__isnull=True)
            | Q(job_warm_pool_utilizations__invoice__isnull=True)
        ).distinct()

        missing_invoice_challenges = []
        for challenge in challenges_with_unlinked_utilization:
            self.stdout.write(
                self.style.WARNING(
                    f"[{challenge.short_name}] Has unlinked utilization."
                )
            )
            try:
                self._link_challenge_utilization(challenge=challenge)
            except NoInvoiceError:
                missing_invoice_challenges.append(challenge.short_name)
                self.stdout.write(
                    self.style.ERROR(
                        f"[{challenge.short_name}] Has no invoices, skipping."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Finished linking utilizations."))

        if missing_invoice_challenges:
            self.stdout.write(
                self.style.ERROR(
                    f"No invoice found for challenges: {', '.join(missing_invoice_challenges)}."
                )
            )

    def _link_challenge_utilization(self, *, challenge):
        invoice = (
            Invoice.objects.filter(challenge=challenge)
            .order_by("expires_on", "created")
            .first()
        )

        if not invoice:
            raise NoInvoiceError
        else:
            for utilization_model in CHALLENGE_UTILIZATION_MODELS:
                utilization_model.objects.filter(
                    challenge=challenge,
                    invoice__isnull=True,
                ).update(invoice=invoice)

            self.stdout.write(
                self.style.SUCCESS(
                    f"{challenge.short_name} Linked utilizations to invoice {invoice.pk}."
                )
            )
