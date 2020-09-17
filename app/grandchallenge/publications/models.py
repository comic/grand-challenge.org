import re
from copy import deepcopy
from pathlib import Path

from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.source.json import CiteProcJSON
from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models

from grandchallenge.core.templatetags.bleach import clean

doi_validator = RegexValidator(
    regex=r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", flags=re.IGNORECASE
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

    citeproc_json = JSONField(editable=False)

    # Metadata that is indexed from citeproc_json
    title = models.TextField(editable=False)
    referenced_by_count = models.PositiveIntegerField(
        editable=False, null=True
    )
    year = models.PositiveIntegerField(editable=False, null=True)

    def __str__(self):
        return f"{self.doi} {self.title}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._citeproc_json_orig = deepcopy(self.citeproc_json)

    def save(self, *args, **kwargs):
        if (
            self._state.adding
            or self._citeproc_json_orig != self.citeproc_json
        ):
            self.update_metadata()

        super().save(*args, **kwargs)

    def update_metadata(self):
        reference = self.bib_source[self.bib_id]

        self.title = str(reference.get("title", ""))
        self.year = reference.get("issued", {}).get("year")

        try:
            self.referenced_by_count = int(
                str(reference.get("is_referenced_by_count"))
            )
        except ValueError:
            self.referenced_by_count = None

    @property
    def bib_id(self):
        if self.pk:
            return self.pk
        else:
            return "__publication__"

    @property
    def bib_source(self):
        return CiteProcJSON([{**self.citeproc_json, "id": self.bib_id}])

    @property
    def ama_html(self):
        if not self.citeproc_json:
            return ""

        bibliography = CitationStylesBibliography(
            CitationStylesStyle(
                str(
                    Path(__file__).parent
                    / "styles"
                    / "american-medical-association-no-url.csl"
                )
            ),
            self.bib_source,
            formatter.html,
        )
        bibliography.register(Citation([CitationItem(self.bib_id)]))

        # The bibliography only contains 1 element
        citation = str(bibliography.bibliography()[0])
        citation = re.sub(r"^1\. ", "", citation)

        return clean(citation)
