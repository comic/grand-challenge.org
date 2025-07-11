from bs4 import BeautifulSoup
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Max
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django_extensions.db.fields import AutoSlugField

from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.subdomains.utils import reverse


class DocPage(models.Model):

    UP = "UP"
    DOWN = "DOWN"
    FIRST = "FIRST"
    LAST = "LAST"

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=1024)
    slug = AutoSlugField(populate_from="title", max_length=1024)

    content = models.TextField()
    content_plain = models.TextField(default="", editable=False)
    search_vector = SearchVectorField(default="", editable=False)

    order = models.IntegerField(
        editable=False,
        default=1,
        help_text="Determines order in which pages appear in side menu",
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    is_faq = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        indexes = [
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # when saving for the first time only, put this page last in order
        if not self.id and not self.parent:
            # get max value of order for current pages.
            try:
                self.order = (
                    DocPage.objects.filter(is_faq=self.is_faq).aggregate(
                        Max("order")
                    )["order__max"]
                    + 1
                )
            except (ObjectDoesNotExist, TypeError):
                # Use the default
                pass
        elif not self.id and self.parent:
            try:
                self.order = (
                    DocPage.objects.filter(slug=self.parent.slug)
                    .get()
                    .children.last()
                    .order
                    + 1
                )
            except AttributeError:
                self.order = (
                    DocPage.objects.filter(slug=self.parent.slug).get().order
                    + 1
                )

        self.update_content_plain()

        super().save(*args, **kwargs)

        DocPage.objects.filter(pk=self.pk).update(
            search_vector=SearchVector("title", "content_plain")
        )

    def update_content_plain(self):
        self.content_plain = BeautifulSoup(
            md2html(self.content, create_permalink_for_headers=False),
            "html.parser",
        ).get_text()

    def position(self, position):
        if position:
            direction = "up" if self.order > position else "down"
            original_pos = self.order
            self.order = position
            self.save()
            if direction == "up":
                pages = (
                    DocPage.objects.exclude(slug=self.slug)
                    .filter(order__gt=position - 1)
                    .all()
                )
                for page in pages:
                    page.order += 1
            else:
                pages = (
                    DocPage.objects.exclude(slug=self.slug)
                    .filter(order__lt=position + 1, order__gt=original_pos)
                    .all()
                )
                for page in pages:
                    page.order -= 1
            DocPage.objects.bulk_update(pages, ["order"])
            self.normalize_page_order(DocPage.objects.all())

    @staticmethod
    def normalize_page_order(pages):
        """Make sure order in pages Queryset starts at 1 and increments 1 at
        every page. Saves all pages
        """
        for idx, page in enumerate(pages):
            page.order = idx + 1
        DocPage.objects.bulk_update(pages, ["order"])

    def get_absolute_url(self):
        url = reverse("documentation:detail", kwargs={"slug": self.slug})
        return url

    @cached_property
    def next(self):
        if self.is_faq:
            raise NotImplementedError(
                "Property 'next' is not implemented for FAQ pages."
            )
        try:
            next_page = DocPage.objects.filter(
                order__gt=self.order, is_faq=False
            ).first()
        except ObjectDoesNotExist:
            next_page = None
        return next_page

    @cached_property
    def previous(self):
        if self.is_faq:
            raise NotImplementedError(
                "Property 'previous' is not implemented for FAQ pages."
            )
        try:
            previous_page = DocPage.objects.filter(
                order__lt=self.order, is_faq=False
            ).last()
        except ObjectDoesNotExist:
            previous_page = None
        return previous_page


@receiver(post_save, sender=DocPage)
def update_page_order(sender, instance, created, **_):
    if created:
        instance.normalize_page_order(
            DocPage.objects.order_by("order", "-modified").all()
        )
