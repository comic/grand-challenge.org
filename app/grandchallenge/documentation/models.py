from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _
from django_extensions.db.fields import AutoSlugField
from simple_history.models import HistoricalRecords

from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.utils.query import index
from grandchallenge.subdomains.utils import reverse


class LevelChoices(models.TextChoices):
    """Documentation page level options"""

    PRIMARY = "PRIMARY", _("Top level")
    SECONDARY = "SECONDARY", _("Second level")
    TERTIARY = "TERTIARY", _("Third level")


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

    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.PRIMARY,
        help_text=(
            "As which level should this page be displayed in the sidebar?"
        ),
    )

    order = models.IntegerField(
        editable=False,
        default=1,
        help_text="Determines order in which pages appear in side menu",
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # when saving for the first time only, put this page last in order
        if not self.id:
            # get max value of order for current pages.
            try:
                max_order = DocPage.objects.aggregate(Max("order"))
            except ObjectDoesNotExist:
                max_order = None
            try:
                self.order = max_order["order__max"] + 1
            except TypeError:
                self.order = 1

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

    # this property will be used to conditionally add a dropdown to higher level pages
    @property
    def next(self):
        try:
            next_page = DocPage.objects.filter(order=self.order + 1).get()
        except ObjectDoesNotExist:
            next_page = None
        return next_page
