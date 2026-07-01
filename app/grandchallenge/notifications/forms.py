from actstream.models import Follow
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms import HiddenInput, ModelForm
from guardian.utils import get_anonymous_user


class FollowForm(ModelForm):
    def __init__(self, *, user, follow_object, **kwargs):
        super().__init__(**kwargs)

        self.fields["user"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["user"].initial = user.pk
        self.fields["content_type"].initial = (
            ContentType.objects.get_for_model(follow_object).pk
        )
        self.fields["object_id"].initial = follow_object.pk
        self.fields["actor_only"].initial = False

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user == get_anonymous_user():
            raise ValidationError(
                "Subscription cannot be created for this user"
            )
        return user

    class Meta:
        model = Follow
        fields = ("user", "content_type", "object_id", "actor_only")
        widgets = {
            "user": HiddenInput(),
            "content_type": HiddenInput(),
            "object_id": HiddenInput(),
            "actor_only": HiddenInput(),
        }
