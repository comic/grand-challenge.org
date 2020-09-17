from copy import deepcopy
from re import IGNORECASE

from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models
from django.template.defaultfilters import truncatechars

doi_validator = RegexValidator(
    regex=r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", flags=IGNORECASE
)


class Publication(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    doi = models.CharField(
        max_length=255,
        # regex modified for python syntax from
        # https://www.crossref.org/blog/dois-and-matching-regular-expressions/
        validators=[doi_validator],
        unique=True,
        help_text="The DOI, e.g., 10.1002/mrm.25227",
    )

    citeproc_json = JSONField(default=dict, editable=False)
    title = models.TextField(editable=False)
    referenced_by_count = models.PositiveIntegerField(editable=False)

    def __str__(self):
        return f"{self.doi} {truncatechars(self.title,20)}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._citeproc_json_orig = deepcopy(self.citeproc_json)

    def save(self, *args, **kwargs):
        if self._citeproc_json_orig != self.citeproc_json:
            self.update_metadata()

        super().save(*args, **kwargs)

    def update_metadata(self):
        self.title = self.citeproc_json.get("title", "")
        self.referenced_by_count = self.citeproc_json.get(
            "is-referenced-by-count", 0
        )
