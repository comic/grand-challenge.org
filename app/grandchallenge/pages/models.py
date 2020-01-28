import json

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Count, Max
from django.template.loader import render_to_string
from django.utils.html import format_html
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.utils.query import index
from grandchallenge.pages.substitutions import Substitution
from grandchallenge.subdomains.utils import reverse


class Page(models.Model):
    """Customisable content that belongs to a challenge."""

    UP = "UP"
    DOWN = "DOWN"
    FIRST = "FIRST"
    LAST = "LAST"

    ALL = "ALL"
    REGISTERED_ONLY = "REG"
    ADMIN_ONLY = "ADM"
    STAFF_ONLY = "STF"

    PERMISSIONS_CHOICES = (
        (ALL, "All"),
        (REGISTERED_ONLY, "Registered users only"),
        (ADMIN_ONLY, "Administrators only"),
    )

    title = models.SlugField(max_length=64, blank=False)
    challenge = models.ForeignKey(
        Challenge,
        help_text="Which challenge does this page belong to?",
        on_delete=models.CASCADE,
    )
    permission_level = models.CharField(
        max_length=3, choices=PERMISSIONS_CHOICES, default=ALL
    )
    order = models.IntegerField(
        editable=False,
        default=1,
        help_text="Determines order in which page appear in site menu",
    )
    display_title = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text=(
            "On pages and in menu items, use this text. Spaces and special "
            "chars allowed here. Optional field. If emtpy, title is used"
        ),
    )
    hidden = models.BooleanField(
        default=False, help_text="Do not display this page in site menu"
    )
    html = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # when saving for the first time only, put this page last in order
        if not self.id:
            # get max value of order for current pages.
            try:
                max_order = Page.objects.filter(
                    challenge=self.challenge
                ).aggregate(Max("order"))
            except ObjectDoesNotExist:
                max_order = None
            try:
                self.order = max_order["order__max"] + 1
            except TypeError:
                self.order = 1

        super().save(*args, **kwargs)

        self.assign_permissions()

    def assign_permissions(self):
        """Give the right groups permissions to this object."""
        admins_group = self.challenge.admins_group
        participants_group = self.challenge.participants_group

        if self.permission_level == self.ALL:
            assign_perm(f"view_{self._meta.model_name}", admins_group, self)
            assign_perm(
                f"view_{self._meta.model_name}", participants_group, self
            )
        elif self.permission_level == self.REGISTERED_ONLY:
            assign_perm(f"view_{self._meta.model_name}", admins_group, self)
            assign_perm(
                f"view_{self._meta.model_name}", participants_group, self
            )
        elif self.permission_level == self.ADMIN_ONLY:
            assign_perm(f"view_{self._meta.model_name}", admins_group, self)
            remove_perm(
                f"view_{self._meta.model_name}", participants_group, self
            )
        else:
            raise ValueError(
                f"Unknown permissions level '{self.permission_level}'. "
                "I don't know which groups to give permissions to this object"
            )

    def can_be_viewed_by(self, user):
        """Is user allowed to view this?"""
        if self.permission_level == self.ALL:
            return True
        else:
            return user.has_perm(f"view_{self._meta.model_name}", self)

    def cleaned_html(self):
        out = clean(self.html)

        if "project_statistics" in out:
            out = self._substitute_geochart(html=out)

        if "google_group" in out:
            s = Substitution(
                tag_name="google_group",
                replacement=render_to_string(
                    "grandchallenge/partials/google_group.html"
                ),
                use_arg=True,
            )
            out = s.sub(out)

        return out

    def _substitute_geochart(self, *, html):
        users = self.challenge.get_participants().select_related(
            "user_profile"
        )
        country_data = (
            users.exclude(user_profile__country="")
            .values("user_profile__country")
            .annotate(country_count=Count("user_profile__country"))
            .order_by("-country_count")
            .values_list("user_profile__country", "country_count")
        )
        content = render_to_string(
            "grandchallenge/partials/geochart.html",
            {
                "user_count": users.count(),
                "country_data": json.dumps(
                    [["Country", "#Participants"]] + list(country_data)
                ),
            },
        )

        s = Substitution(
            tag_name="project_statistics",
            replacement=format_html("<h1>Statistics</h1>{}", content),
        )
        return s.sub(html)

    def move(self, move):
        if move == self.UP:
            mm = Page.objects.get(
                challenge=self.challenge, order=self.order - 1
            )
            mm.order += 1
            mm.save()
            self.order -= 1
            self.save()
        elif move == self.DOWN:
            mm = Page.objects.get(
                challenge=self.challenge, order=self.order + 1
            )
            mm.order -= 1
            mm.save()
            self.order += 1
            self.save()
        elif move == self.FIRST:
            pages = Page.objects.filter(challenge=self.challenge)
            idx = index(pages, self)
            pages[idx].order = pages[0].order - 1
            pages = sorted(pages, key=lambda page: page.order)
            self.normalize_page_order(pages)
        elif move == self.LAST:
            pages = Page.objects.filter(challenge=self.challenge)
            idx = index(pages, self)
            pages[idx].order = pages[len(pages) - 1].order + 1
            pages = sorted(pages, key=lambda page: page.order)
            self.normalize_page_order(pages)

    @staticmethod
    def normalize_page_order(pages):
        """Make sure order in pages Queryset starts at 1 and increments 1 at
        every page. Saves all pages

        """
        for idx, page in enumerate(pages):
            page.order = idx + 1
            page.save()

    def get_absolute_url(self):
        url = reverse(
            "pages:detail",
            kwargs={
                "challenge_short_name": self.challenge.short_name,
                "page_title": self.title,
            },
        )
        return url

    class Meta:
        # make sure a single site never has two pages with the same name
        # because page names are used as keys in urls
        unique_together = (("challenge", "title"),)
        # when getting a list of these objects this ordering is used
        ordering = ["challenge", "order"]


class ErrorPage(Page):
    """
    Just the same as a Page, just that it does not display an edit button as
    admin
    """

    is_error_page = True

    def can_be_viewed_by(self, user):
        """Allow all users to view ErrorPages."""
        return True

    class Meta:
        abstract = True  # error pages should only be generated on the fly
