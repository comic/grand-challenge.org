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
from citeproc.source import Name
from citeproc.source.json import CiteProcJSON
from django.db import models

from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.publications.fields import IdentifierField


class ConsortiumNameCiteProcJSON(CiteProcJSON):
    """CiteProcJSON, but handles consortium names"""

    def parse_names(self, json_data):
        names = []
        for name_data in json_data:
            if "family" not in name_data and "name" in name_data:
                # Handle consortium data
                name_data["family"] = name_data.pop("name")
            name = Name(**name_data)
            names.append(name)
        return names


class Publication(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    identifier = IdentifierField(
        unique=True,
        help_text="The DOI, e.g., 10.1002/mrm.25227, or the arXiv id, e.g., 2006.12449",
    )

    csl = models.JSONField(editable=False)

    # Metadata that is indexed from the csl
    title = models.TextField(editable=False)
    referenced_by_count = models.PositiveIntegerField(
        editable=False, null=True
    )
    year = models.PositiveIntegerField(editable=False, null=True)
    citation = models.TextField(editable=False, blank=True)

    def __str__(self):
        return clean(f"{self.identifier} {self.citation}")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._csl_orig = deepcopy(self.csl)

    def save(self, *args, **kwargs):
        if self._state.adding or self._csl_orig != self.csl:
            self.update_metadata()

        super().save(*args, **kwargs)

    def update_metadata(self):
        reference = self.bib_source[self.bib_id]

        self.title = str(reference.get("title", ""))
        self.year = reference.get("issued", {}).get("year")
        self.citation = self.ama_html

        try:
            self.referenced_by_count = int(
                str(reference.get("is_referenced_by_count"))
            )
        except ValueError:
            self.referenced_by_count = None

    @classmethod
    def get_reverse_many_to_many_fields(cls):
        """
        Return the reverse relations to models that include
        this class as a many-to-many field.
        """
        reverse_relations = []
        for field in cls._meta.get_fields():
            if field.is_relation and field.many_to_many:
                reverse_relations.append(field.get_accessor_name())
        return reverse_relations

    @property
    def bib_id(self):
        if self.pk:
            return str(self.pk)
        else:
            return "__publication__"

    @property
    def bib_source(self):
        return ConsortiumNameCiteProcJSON([{**self.csl, "id": self.bib_id}])

    @property
    def ama_html(self):
        if not self.csl:
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

    @property
    def authors(self):
        return [a.get("family") for a in self.csl.get("author", [])]
