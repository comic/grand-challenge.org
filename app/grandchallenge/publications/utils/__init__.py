import re

import requests
from django.db.models import TextChoices

from grandchallenge.publications.models import ARXIV_REGEX, DOI_REGEX
from grandchallenge.publications.utils.manubot import get_arxiv_csl


class PublicationType(TextChoices):
    DOI = "D"
    ARXIV = "A"


def get_publication_type(*, identifier: str) -> PublicationType:
    if re.match(DOI_REGEX, identifier):
        return PublicationType.DOI
    elif re.match(ARXIV_REGEX, identifier):
        return PublicationType.ARXIV
    else:
        raise ValueError(
            f"Could not determine publication type from {identifier}"
        )


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
            new_id = csl["DOI"]
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
    )

    if response.status_code != 200:
        raise ValueError("DOI not found")

    return response.json()
