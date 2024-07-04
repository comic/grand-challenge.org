import requests
from django.core.exceptions import ObjectDoesNotExist


def get_doi_csl(*, doi):
    response = requests.get(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/vnd.citationstyles.csl+json"},
        timeout=5,
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            raise ObjectDoesNotExist(f"DOI {doi} not found") from e
        else:
            raise

    return response.json()
