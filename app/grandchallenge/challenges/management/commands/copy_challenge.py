import re

from django.contrib.sites.models import Site
from django.core.management import BaseCommand, CommandError

from grandchallenge.challenges.models import Challenge
from grandchallenge.pages.models import Page


class Command(BaseCommand):
    help = "Creates a copy of a challenge"

    challenge_fields = [
        "creator",
        "description",
        "educational",
        "disclaimer",
        "require_participant_review",
        "use_registration_page",
        "registration_page_text",
        "use_evaluation",
        "logo",
        "banner",
    ]

    challenge_m2m_fields = [
        "task_types",
        "modalities",
        "structures",
    ]

    config_fields = [
        "use_teams",
        "score_title",
        "score_jsonpath",
        "score_error_jsonpath",
        "score_default_sort",
        "score_decimal_places",
        "extra_results_columns",
        "scoring_method_choice",
        "result_display_choice",
        "allow_submission_comments",
        "display_submission_comments",
        "supplementary_file_choice",
        "supplementary_file_label",
        "supplementary_file_help_text",
        "show_supplementary_file_link",
        "publication_url_choice",
        "show_publication_url",
        "daily_submission_limit",
        "submission_page_html",
        "auto_publish_new_results",
        "display_all_metrics",
        "submission_join_key",
    ]

    page_fields = [
        "title",
        "permission_level",
        "order",
        "display_title",
        "hidden",
    ]

    def add_arguments(self, parser):
        parser.add_argument("source", type=str)
        parser.add_argument("dest", type=str)

    def handle(self, *args, **options):
        src_name = options.pop("source")
        dest_name = options.pop("dest")

        if src_name.lower() == dest_name.lower():
            raise CommandError("Source and dest names must be different")

        src_challenge = Challenge.objects.get(short_name__iexact=src_name)
        dest_challenge = self._create_new_challenge(
            src_challenge=src_challenge, dest_name=dest_name
        )

        self._copy_m2m_fields(
            src_challenge=src_challenge, dest_challenge=dest_challenge
        )
        self._copy_evaluation_config(
            src_challenge=src_challenge, dest_challenge=dest_challenge
        )
        self._copy_pages(
            src_challenge=src_challenge, dest_challenge=dest_challenge
        )
        self._copy_admins(
            src_challenge=src_challenge, dest_challenge=dest_challenge
        )

    def _create_new_challenge(self, *, src_challenge, dest_name):
        new_challenge = Challenge(
            short_name=dest_name,
            **{f: getattr(src_challenge, f) for f in self.challenge_fields},
        )
        new_challenge.full_clean()
        new_challenge.save()
        return new_challenge

    def _copy_m2m_fields(self, *, src_challenge, dest_challenge):
        for f in self.challenge_m2m_fields:
            src_m2m = getattr(src_challenge, f)
            dest_m2m = getattr(dest_challenge, f)
            dest_m2m.set(src_m2m.all())

    def _copy_evaluation_config(self, *, src_challenge, dest_challenge):
        src_config = src_challenge.evaluation_config
        dest_config = dest_challenge.evaluation_config

        for attr in self.config_fields:
            setattr(dest_config, attr, getattr(src_config, attr))

        dest_config.save()

    def _substitute_urls(self, html, domain, old, new):
        quote_replace = r"href='([^']*)'"
        regex = fr'href="[^/]*//{old}.{domain}([^""]*)"'
        html = re.sub(quote_replace, r'href="\1"', html)
        return re.sub(regex, fr'href="https://{new}.{domain}\1"', html,)

    def _copy_pages(self, *, src_challenge, dest_challenge):
        src_pages = src_challenge.page_set.all()

        site = Site.objects.get_current()
        domain = site.domain
        old = src_challenge.short_name
        new = dest_challenge.short_name

        for src_page in src_pages:
            Page.objects.create(
                challenge=dest_challenge,
                html=self._substitute_urls(src_page.html, domain, old, new),
                **{f: getattr(src_page, f) for f in self.page_fields},
            )

    def _copy_admins(self, *, src_challenge, dest_challenge):
        for u in src_challenge.get_admins():
            dest_challenge.add_admin(u)
