from django import forms
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from grandchallenge.publications.fields import PublicationIdentifier
from grandchallenge.publications.models import Publication


class PublicationForm(forms.ModelForm):
    def clean(self):
        self.cleaned_data = super().clean()

        if self.errors:
            return self.cleaned_data

        identifier = self.cleaned_data.get(
            "identifier", self.instance.identifier
        )

        try:
            csl, new_identifier = PublicationIdentifier(identifier).csl
        except ObjectDoesNotExist:
            raise ValidationError(
                f"Identifier {identifier} not found. "
                "Please check that you have provided the correct reference. "
                "If this article was recently published, it may not be indexed yet. "
                "Please try again later."
            )
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
