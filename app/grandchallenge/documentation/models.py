from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from django_extensions.db.fields import AutoSlugField
from simple_history.models import HistoricalRecords

from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.utils.query import index
from grandchallenge.subdomains.utils import reverse


class LevelChoices(models.IntegerChoices):
    """Documentation page level options"""

    PRIMARY = 1, _("Top level")
    SECONDARY = 2, _("Second level")
    TERTIARY = 3, _("Third level")


class DocPageLevel:
    """Documentation page level."""

    DocPageLevelChoices = LevelChoices


class DocPage(models.Model):

    Level = DocPageLevel.DocPageLevelChoices

    UP = "UP"
    DOWN = "DOWN"
    FIRST = "FIRST"
    LAST = "LAST"

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=1024)
    slug = AutoSlugField(populate_from="title", max_length=1024)
    display_title = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text=(
            "On pages and in menu items, use this text. Spaces and special "
            "chars allowed here. Optional field. If emtpy, title is used"
        ),
    )

    content = models.TextField()

    level = models.PositiveSmallIntegerField(
        default=Level.PRIMARY,
        choices=Level.choices,
        help_text=(
            "As which level should this page be displayed in the sidebar?"
        ),
    )

    order = models.IntegerField(
        editable=False,
        default=1,
        help_text="Determines order in which pages appear in side menu",
    )

    history = HistoricalRecords(excluded_fields=["level", "order"])

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # when saving for the first time only, put this page last in order
        if not self.id:
            # get max value of order for current pages.
            try:
                self.order = (
                    DocPage.objects.aggregate(Max("order"))["order__max"] + 1
                )
            except ObjectDoesNotExist:
                # Use the default
                pass
            except TypeError:
                # Use the default
                pass

        self.html = clean(self.content)

        super().save(*args, **kwargs)

    def move(self, move):
        if move == self.UP:
            mm = DocPage.objects.get(order=self.order - 1)
            mm.order += 1
            mm.save()
            self.order -= 1
            self.save()
        elif move == self.DOWN:
            mm = DocPage.objects.get(order=self.order + 1)
            mm.order -= 1
            mm.save()
            self.order += 1
            self.save()
        elif move == self.FIRST:
            pages = DocPage.objects.all()
            idx = index(pages, self)
            pages[idx].order = pages[0].order - 1
            pages = sorted(pages, key=lambda page: page.order)
            self.normalize_page_order(pages)
        elif move == self.LAST:
            pages = DocPage.objects.all()
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
        url = reverse("documentation:detail", kwargs={"slug": self.slug},)
        return url

    @property
    def next(self):
        try:
            next_page = DocPage.objects.filter(order=self.order + 1).get()
        except ObjectDoesNotExist:
            next_page = None
        return next_page

    @property
    def previous(self):
        try:
            previous_page = DocPage.objects.filter(order=self.order - 1).get()
        except ObjectDoesNotExist:
            previous_page = None
        return previous_page

    @property
    def parent(self):
        if self.level == "PRIMARY":
            parent = None
        else:
            if self.level == "SECONDARY":
                parent = DocPage.objects.filter(
                    order__lt=self.order, level="PRIMARY"
                ).last()
            elif self.level == "TERTIARY":
                parent = DocPage.objects.filter(
                    order__lt=self.order, level="SECONDARY"
                ).last()
        return parent

    @property
    def children(self):
        if self.level == "PRIMARY":
            children = DocPage.objects.filter(
                order__gt=self.order, level="SECONDARY"
            ).all()
        elif self.level == "SECONDARY":
            children = DocPage.objects.filter(
                order__gt=self.order, level="TERTIARY"
            ).all()
        elif self.level == "TERTIARY":
            children = None
        return children
