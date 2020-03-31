from django.db.models import BooleanField, Index, ManyToManyField, TextField
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class OverviewPage(TitleSlugDescriptionModel, UUIDModel):
    """
    An overview page shows up as a main item in the top navigation menu and
    allows linking together of other objects.
    """

    detail_page_markdown = TextField(blank=True)

    algorithms = ManyToManyField("algorithms.Algorithm", blank=True)
    archives = ManyToManyField("archives.Archive", blank=True)
    challenges = ManyToManyField("challenges.Challenge", blank=True)
    reader_studies = ManyToManyField("reader_studies.ReaderStudy", blank=True)

    published = BooleanField(default=False)

    class Meta(TitleSlugDescriptionModel.Meta, UUIDModel.Meta):
        ordering = ("-created",)
        indexes = (Index(fields=["published"]),)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("overview-pages:detail", kwargs={"slug": self.slug})
