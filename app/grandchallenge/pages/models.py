import difflib

from bs4 import BeautifulSoup
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import mail_managers
from django.db import models
from django.db.models import Max
from django.utils.html import format_html
from django_extensions.db.fields import AutoSlugField
from guardian.shortcuts import assign_perm, remove_perm
from simple_history.models import HistoricalRecords

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import FieldChangeMixin
from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.core.utils.query import index
from grandchallenge.subdomains.utils import reverse


class Page(FieldChangeMixin, models.Model):
    """Customisable content that belongs to a challenge."""

    UP = "UP"
    DOWN = "DOWN"
    FIRST = "FIRST"
    LAST = "LAST"

    ALL = "ALL"
    REGISTERED_ONLY = "REG"
    ADMIN_ONLY = "ADM"

    PERMISSIONS_CHOICES = (
        (ALL, "All"),
        (REGISTERED_ONLY, "Participants only"),
        (ADMIN_ONLY, "Administrators only"),
    )

    created = models.DateTimeField(auto_now_add=True, null=True)
    modified = models.DateTimeField(auto_now=True, null=True)
    display_title = models.CharField(
        max_length=255,
        blank=False,
    )
    slug = AutoSlugField(populate_from="display_title", max_length=64)
    challenge = models.ForeignKey(
        "challenges.Challenge",
        help_text="Which challenge does this page belong to?",
        on_delete=models.PROTECT,
    )
    permission_level = models.CharField(
        max_length=3, choices=PERMISSIONS_CHOICES, default=ALL
    )
    order = models.IntegerField(
        editable=False,
        default=1,
        help_text="Determines order in which page appear in site menu",
    )
    hidden = models.BooleanField(
        default=False, help_text="Do not display this page in site menu"
    )
    content_markdown = models.TextField(blank=True)
    history = HistoricalRecords(
        excluded_fields=[
            "slug",
        ]
    )

    def __str__(self):
        if self.display_title:
            return self.display_title
        else:
            return self.slug

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            # when saving for the first time only, put this page last in order
            try:
                # get max value of order for current pages.
                max_order = Page.objects.filter(
                    challenge=self.challenge
                ).aggregate(Max("order"))
            except ObjectDoesNotExist:
                max_order = None
            try:
                self.order = max_order["order__max"] + 1
            except TypeError:
                self.order = 1
        elif not self.challenge.is_active and self.has_changed(
            "content_markdown"
        ):
            self.handle_changed_content_for_inactive_challenge()

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
                f"Unknown permissions level {self.permission_level!r}. "
                "I don't know which groups to give permissions to this object"
            )

    def can_be_viewed_by(self, user):
        """Is user allowed to view this?"""
        if self.permission_level == self.ALL:
            return True
        else:
            return user.has_perm(f"view_{self._meta.model_name}", self)

    def move(self, move):
        if move == self.UP:
            target_page = (
                Page.objects.filter(
                    challenge=self.challenge, order__lt=self.order
                )
                .order_by("order")
                .last()
            )
            if target_page:
                target_order = target_page.order
                target_page.order = self.order
                target_page.save()

                self.order = target_order
                self.save()
        elif move == self.DOWN:
            target_page = (
                Page.objects.filter(
                    challenge=self.challenge, order__gt=self.order
                )
                .order_by("order")
                .first()
            )
            if target_page:
                target_order = target_page.order
                target_page.order = self.order
                target_page.save()

                self.order = target_order
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
                "slug": self.slug,
            },
        )
        return url

    @staticmethod
    def get_visible_text(html):
        return (
            BeautifulSoup(html, "html.parser")
            .get_text(separator="\n")
            .strip()
            .splitlines()
        )

    def handle_changed_content_for_inactive_challenge(self):
        old_content = self.get_visible_text(
            md2html(self.initial_value("content_markdown"))
        )
        new_content = self.get_visible_text(md2html(self.content_markdown))

        diff = "\n".join(
            difflib.unified_diff(old_content, new_content, lineterm="")
        )

        if diff:
            mail_managers(
                subject=f"[{self.challenge.slug}] Page updated for inactive challenge",
                message=format_html(
                    (
                        "{page_url} was updated whilst the challenge is inactive. "
                        "Here are the changes:\n\n{diff}"
                    ),
                    page_url=self.get_absolute_url(),
                    diff=diff,
                ),
            )

    class Meta:
        # make sure a single site never has two pages with the same name
        # because page names are used as keys in urls
        unique_together = (("challenge", "slug"),)
        # when getting a list of these objects this ordering is used
        ordering = ["challenge", "order"]


class PageUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Page, on_delete=models.CASCADE)


class PageGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Page, on_delete=models.CASCADE)
