import re

from django.core.validators import RegexValidator
from django.db import models
from django.forms import CharField

from grandchallenge.publications.utils import get_doi_csl
from grandchallenge.publications.utils.manubot import get_arxiv_csl

# regex modified for python syntax from
# https://www.crossref.org/blog/dois-and-matching-regular-expressions/
DOI_REGEX = r"^10\.\d{4,9}/[-._;()/:a-z0-9]+$"
ARXIV_REGEX = r"^\d{4}\.\d{4,5}$"

identifier_validator = RegexValidator(regex=f"{DOI_REGEX}|{ARXIV_REGEX}")


class PublicationType(models.TextChoices):
    DOI = "D"
    ARXIV = "A"


class PublicationIdentifier:
    def __init__(self, identifier):
        self._identifier = identifier.lower()

    def __len__(self):
        return len(self._identifier)

    def __str__(self):
        return str(self._identifier)

    @property
    def kind(self):
        if re.match(DOI_REGEX, self._identifier):
            return PublicationType.DOI
        elif re.match(ARXIV_REGEX, self._identifier):
            return PublicationType.ARXIV
        else:
            raise ValueError(
                f"Could not determine publication type from {self._identifier}"
            )

    @property
    def url(self):
        if self.kind == PublicationType.ARXIV:
            return f"https://arxiv.org/abs/{self._identifier}"
        elif self.kind == PublicationType.DOI:
            return f"https://doi.org/{self._identifier}"
        else:
            return "#"

    @property
    def csl(self):
        """
        Fetches the csl for the given identifier.

        arXiv pre-prints contain a DOI field in the CSL once they are published,
        if this happens, the identifier is updated and the full DOI information
        is fetched.
        """
        if self.kind == PublicationType.ARXIV:
            new_id = self._identifier
            csl = get_arxiv_csl(arxiv_id=new_id)

            if "DOI" in csl:
                # This arXiv paper is now published, update the identifier and
                # fetch the information from the DOI provider
                new_id = csl["DOI"].lower()
                csl = get_doi_csl(doi=new_id)
        elif self.kind == PublicationType.DOI:
            new_id = self._identifier
            csl = get_doi_csl(doi=new_id)
        else:
            raise ValueError("Identifier not recognised")

        return csl, new_id


def parse_identifier(identifier_string):
    """Takes an identifier string and return an Indentifier instance."""
    return PublicationIdentifier(identifier_string)


class IdentifierField(models.CharField):
    default_validators = [identifier_validator]
    description = "String reflecting a DOI or arXiv id"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 255)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return parse_identifier(value)

    def to_python(self, value):
        if isinstance(value, PublicationIdentifier):
            return value
        if value is None:
            return value
        return parse_identifier(value)

    def get_prep_value(self, value):
        if isinstance(value, PublicationIdentifier):
            return str(value)
        else:
            return value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_length") == 255:
            del kwargs["max_length"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {"form_class": IdentifierFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class IdentifierFormField(CharField):
    default_validators = [identifier_validator]

    def clean(self, value):
        return super().clean(value.lower())
