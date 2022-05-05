import requests


def get_doi_csl(*, doi):
    response = requests.get(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/vnd.citationstyles.csl+json"},
        timeout=5,
    )
    response.raise_for_status()

    return response.json()
