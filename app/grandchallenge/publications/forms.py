import requests
from django import forms

from grandchallenge.publications.models import Publication, doi_validator


class PublicationForm(forms.ModelForm):
    def clean_doi(self):
        doi = self.cleaned_data["doi"]
        doi = doi.lower()
        doi_validator(doi)
        return doi

    def clean(self):
        self.cleaned_data = super().clean()

        if self.errors:
            return self.cleaned_data

        doi = self.cleaned_data.get("doi", self.instance.doi)

        response = requests.get(
            f"https://doi.org/{doi}",
            headers={"Accept": "application/vnd.citationstyles.csl+json"},
        )

        if response.status_code != 200:
            self.add_error("doi", "This DOI could not be found.")
        else:
            self.cleaned_data["citeproc_json"] = response.json()
            self.instance.citeproc_json = response.json()

        return self.cleaned_data

    class Meta:
        model = Publication
        fields = ("doi",)
