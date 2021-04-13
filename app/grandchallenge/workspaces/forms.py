from django import forms
from django.contrib.auth import get_user_model

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.evaluation.models import Phase
from grandchallenge.workspaces.models import Workspace


class WorkspaceForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, user, phase, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["user"].initial = user

        self.fields["phase"].queryset = Phase.objects.filter(pk=phase.pk)
        self.fields["phase"].initial = phase

    class Meta:
        model = Workspace
        fields = (
            "user",
            "phase",
        )
