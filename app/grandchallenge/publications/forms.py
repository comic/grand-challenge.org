import requests
from django import forms

from grandchallenge.publications.models import (
    Publication,
    identifier_validator,
)


class PublicationForm(forms.ModelForm):
    def clean_identifier(self):
        identifier = self.cleaned_data["identifier"]
        identifier = identifier.lower()
        identifier_validator(identifier)
        return identifier

    def clean(self):
        self.cleaned_data = super().clean()

        if self.errors:
            return self.cleaned_data

        identifier = self.cleaned_data.get(
            "identifier", self.instance.identifier
        )

        response = requests.get(
            f"https://doi.org/{identifier}",
            headers={"Accept": "application/vnd.citationstyles.csl+json"},
        )

        if response.status_code != 200:
            self.add_error("identifier", "This identifier could not be found.")
        else:
            self.cleaned_data["citeproc_json"] = response.json()
            self.instance.citeproc_json = response.json()

        return self.cleaned_data

    class Meta:
        model = Publication
        fields = ("identifier",)
