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


class NoInvoiceError(Exception):
    pass


class Command(BaseCommand):
    help = "Links challenge utilizations to invoices"

    def handle(self, *_, **__):

        invoice_by_challenge = {}
        for inv in Invoice.objects.order_by("expires_on", "created"):
            if inv.challenge_id not in invoice_by_challenge:
                invoice_by_challenge[inv.challenge_id] = inv

        missing_invoice_challenges = []
        challenge_count = Challenge.objects.count()

        for indx, challenge in enumerate(Challenge.objects.all()):
            prefix = f"[{challenge.short_name}]"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix} Working on linking utilizations for ({indx + 1}/{challenge_count})."
                )
            )
            try:
                invoice = invoice_by_challenge[challenge.pk]
            except KeyError:
                missing_invoice_challenges.append(challenge.short_name)
                self.stdout.write(
                    self.style.WARNING(
                        f"{prefix} No invoices found, skipping."
                    )
                )
            else:
                for model in CHALLENGE_UTILIZATION_MODELS:
                    rows_updated = model.objects.filter(
                        challenge=challenge,
                        invoice__isnull=True,
                    ).update(invoice=invoice)
                    if rows_updated:
                        self.stdout.write(
                            self.style.WARNING(
                                f"{prefix} {rows_updated} {model.__name__} updated."
                            )
                        )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix} Finished linking utilizations ({indx + 1}/{challenge_count})."
                )
            )

        self.stdout.write(self.style.SUCCESS("Finished linking utilizations."))

        if missing_invoice_challenges:
            self.stdout.write(
                self.style.ERROR(
                    f"No invoice found for {len(missing_invoice_challenges)} challenges: {', '.join(missing_invoice_challenges)}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("All challenges had an invoice to link to.")
            )
