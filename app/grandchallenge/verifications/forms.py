from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.verifications.models import Verification


class VerificationForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["user"].queryset = get_user_model().objects.filter(
            pk=self.user.pk
        )
        self.fields["user"].initial = self.user
        self.fields["user"].widget = forms.HiddenInput()

        self.fields["email"].initial = self.user.email
        self.fields["email"].required = True
        self.fields[
            "email"
        ].help_text = (
            "Please provide your work, corporate or institutional email"
        )

    def clean_email(self):
        email = self.cleaned_data["email"]

        if (
            get_user_model()
            .objects.filter(email__iexact=email)
            .exclude(pk=self.user.pk)
            .exists()
            or Verification.objects.filter(email__iexact=email).exists()
        ):
            raise ValidationError("This email is already in use")

        return email

    def clean(self):
        try:
            if self.user.verification:
                raise ValidationError(
                    "You have already made a verification request"
                )
        except ObjectDoesNotExist:
            pass

    class Meta:
        model = Verification
        fields = ("user", "email")
