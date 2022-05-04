import re

import requests
from django.core.validators import RegexValidator
from django.db import models

from grandchallenge.publications.utils.manubot import get_arxiv_csl

# regex modified for python syntax from
# https://www.crossref.org/blog/dois-and-matching-regular-expressions/
DOI_REGEX = r"^10\.\d{4,9}/[-._;()/:a-z0-9]+$"
ARXIV_REGEX = r"^\d{4}\.\d{4,5}$"

identifier_validator = RegexValidator(regex=f"{DOI_REGEX}|{ARXIV_REGEX}")


class PublicationType(models.TextChoices):
    DOI = "D"
    ARXIV = "A"


class IdentifierField(models.CharField):

    description = (
        "The DOI e.g., 10.1002/mrm.25227, or the arXiv id, e.g., 2006.12449"
    )

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        kwargs[
            "help_text"
        ] = "The DOI, e.g., 10.1002/mrm.25227, or the arXiv id, e.g., 2006.12449"
        kwargs["validators"] = [identifier_validator]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["help_text"]
        del kwargs["validators"]
        return name, path, args, kwargs


def get_publication_type(*, identifier: str) -> PublicationType:
    if re.match(DOI_REGEX, identifier):
        return PublicationType.DOI
    elif re.match(ARXIV_REGEX, identifier):
        return PublicationType.ARXIV
    else:
        raise ValueError(
            f"Could not determine publication type from {identifier}"
        )


def get_publication_url(*, identifier: str, pub_type: PublicationType):
    if pub_type == PublicationType.ARXIV:
        return f"https://arxiv.org/abs/{identifier}"
    elif pub_type == PublicationType.DOI:
        return f"https://doi.org/{identifier}"
    else:
        return "#"


def get_identifier_csl(*, doi_or_arxiv):
    """
    Fetches the csl for the given identifier.

    arXiv pre-prints contain a DOI field in the CSL once they are published,
    if this happens, the identifier is updated and the full DOI information
    is fetched.
    """
    pub_type = get_publication_type(identifier=doi_or_arxiv)

    if pub_type == PublicationType.ARXIV:
        new_id = doi_or_arxiv
        csl = get_arxiv_csl(arxiv_id=new_id)

        if "DOI" in csl:
            # This arXiv paper is now published, update the identifier and
            # fetch the information from the DOI provider
            new_id = csl["DOI"].lower()
            csl = get_doi_csl(doi=new_id)

    elif pub_type == PublicationType.DOI:
        new_id = doi_or_arxiv
        csl = get_doi_csl(doi=new_id)

    else:
        raise ValueError("Identifier not recognised")

    return csl, new_id


def get_doi_csl(*, doi):
    response = requests.get(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/vnd.citationstyles.csl+json"},
        timeout=5,
    )
    response.raise_for_status()

    return response.json()
