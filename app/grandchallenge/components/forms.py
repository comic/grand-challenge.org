from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import HiddenInput, ModelChoiceField, ModelForm
from guardian.shortcuts import get_objects_for_user

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget


class ContainerImageForm(SaveFormInitMixin, ModelForm):
    user_upload = ModelChoiceField(
        widget=UserUploadSingleWidget(),
        label="Container Image",
        queryset=None,
        # TODO set validators
        help_text=(
            ".tar.xz archive of the container image produced from the command "
            "'docker save IMAGE | xz -c > IMAGE.tar.xz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )
    creator = ModelChoiceField(
        widget=HiddenInput(),
        queryset=(
            get_user_model()
            .objects.exclude(username=settings.ANONYMOUS_USER_NAME)
            .filter(verification__is_verified=True)
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user_upload"].queryset = get_objects_for_user(
            user, "change_userupload", UserUpload
        ).filter(status=UserUpload.StatusChoices.COMPLETED)

        self.fields["creator"].initial = user

    class Meta:
        fields = (
            "user_upload",
            "creator",
        )
