from django.core.management.base import BaseCommand

from grandchallenge.challenges.models import Challenge
from grandchallenge.invoices.models import (
    Invoice,
    PaymentStatusChoices,
    PaymentTypeChoices,
)
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


class Command(BaseCommand):
    help = "Links challenge utilizations to invoices, optionally creates a dummy invoice if none exists for a challenge"

    def add_arguments(self, parser):
        parser.add_argument(
            "challenge_short_names",
            nargs="*",
            type=str,
        )

        parser.add_argument(
            "--all_challenges",
            action="store_true",
            help="Link all challenge utilizations to invoices",
        )

        parser.add_argument(
            "--create_missing_invoice",
            action="store_true",
            help="Create an invoice if none exists for a challenge",
        )

    def handle(self, *args, **options):
        if options["all_challenges"]:
            challenges = Challenge.objects.all()
        else:
            challenges = Challenge.objects.filter(
                short_name__in=options["challenge_short_names"]
            )

        for challenge in challenges:
            self._link_challenge_utilization(
                challenge=challenge,
                create_missing_invoice=options["create_missing_invoice"],
            )

        self.stdout.write(self.style.SUCCESS("Finished linking utilizations"))

    def _link_challenge_utilization(
        self, *, challenge, create_missing_invoice
    ):
        prefix = f"[{challenge.short_name}]"

        has_unlinked = any(
            utilization_model.objects.filter(
                challenge=challenge, invoice__isnull=True
            ).exists()
            for utilization_model in CHALLENGE_UTILIZATION_MODELS
        )
        if not has_unlinked:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{prefix} No unlinked utilizations found, skipping."
                )
            )
            return
        else:
            self.stdout.write(
                self.style.WARNING(f"{prefix} Found unlinked utilizations.")
            )

        invoice = (
            Invoice.objects.filter(challenge=challenge)
            .order_by("expires_on", "created")
            .first()
        )

        if not invoice:
            if not create_missing_invoice:
                self.stdout.write(
                    self.style.ERROR(f"{prefix} No invoice found.")
                )
                return

            self.stdout.write(
                self.style.WARNING(
                    f"{prefix} No target invoice found, creating invoice."
                )
            )
            invoice = Invoice.objects.create(
                challenge=challenge,
                support_costs_euros=0,
                compute_costs_euros=0,
                storage_costs_euros=0,
                payment_type=PaymentTypeChoices.COMPLIMENTARY,
                payment_status=PaymentStatusChoices.CANCELLED,
                internal_comments="Created to link utilizations without existing invoices. This invoice represents historical compute usage that was not tracked under any invoice.",
            )

        for utilization_model in CHALLENGE_UTILIZATION_MODELS:
            utilization_model.objects.filter(
                challenge=challenge,
                invoice__isnull=True,
            ).update(invoice=invoice)

        self.stdout.write(
            self.style.SUCCESS(f"{prefix} Linked utilizations to invoice.")
        )
