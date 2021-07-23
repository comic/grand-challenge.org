import requests

from grandchallenge.publications.models import (
    PublicationType,
    get_publication_type,
)
from grandchallenge.publications.utils.manubot import get_arxiv_csl


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
