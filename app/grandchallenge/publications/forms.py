from django import forms
from django.core.exceptions import ValidationError

from grandchallenge.publications.models import (
    Publication,
    identifier_validator,
)
from grandchallenge.publications.utils import get_identifier_csl


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

        try:
            csl, new_identifier = get_identifier_csl(doi_or_arxiv=identifier)
        except ValueError:
            raise ValidationError("Identifier not recognised")

        if new_identifier != identifier:
            self.cleaned_data["identifier"] = new_identifier
            self.instance.identifier = new_identifier

        self.cleaned_data["csl"] = csl
        self.instance.csl = csl

        return self.cleaned_data

    class Meta:
        model = Publication
        fields = ("identifier",)
