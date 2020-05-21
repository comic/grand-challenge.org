from dataclasses import dataclass
from random import choice

from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    ImproperlyConfigured,
    NON_FIELD_ERRORS,
    ValidationError,
)
from django.forms.utils import ErrorList
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.views.generic import TemplateView, UpdateView
from guardian.mixins import (
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.permissions.mixins import UserIsNotAnonMixin
from grandchallenge.subdomains.utils import reverse


@dataclass
class Highlight:
    title: str
    description: str
    image: str
    url: str


class HomeTemplate(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        background_url = static(
            choice(
                [
                    "images/home_pathology_crop_1_bannersize.jpg",
                    "images/home_ophthalmology_1_bannersize.png",
                    "images/home_radiology_1_bannersize.png",
                    "images/home_radiology_2_bannersize.png",
                ]
            )
        )

        highlights = [
            Highlight(
                title="Archives",
                description=(
                    "Archives are the place to host your dataset if you want "
                    "to create reader studies, challenges or use an "
                    "algorithm. Archives can be kept private or made public."
                ),
                url=reverse("archives:list"),
                image="images/archive_1.jpg",
            ),
            Highlight(
                title="Reader Studies",
                description=(
                    "Reader studies can have many purposes. Need structured "
                    "labels of medical data for algorithm training? Want to "
                    "do an observer study and collect data from multiple "
                    "readers? Wish to create a teaching file or test "
                    "someone’s skills?"
                ),
                url=reverse("reader-studies:list"),
                image="images/challenge_1.jpg",
            ),
            Highlight(
                title="Challenges",
                description=(
                    "Challenges allow for a fair and transparent comparison "
                    "of algorithms. Created an algorithm with the same "
                    "purpose as one of the existing challenges? Join the "
                    "challenge and see how well it performs. Or create a "
                    "challenge yourself."
                ),
                url=reverse("challenges:list"),
                image="images/challenge_2.jpg",
            ),
            Highlight(
                title="Algorithms",
                description=(
                    "Once the algorithms are developed enough to be shared "
                    "with the world, this is the place. Use algorithms by "
                    "uploading your images. Or add your own algorithm."
                ),
                url=reverse("algorithms:list"),
                image="images/algorithms_1.png",
            ),
        ]

        context.update(
            {
                "all_users": get_user_model().objects.all(),
                "all_challenges": Challenge.objects.all(),
                "all_algorithms": Algorithm.objects.all(),
                "highlights": highlights,
                "background_url": background_url,
            }
        )
        return context


class PermissionRequestUpdate(
    UserIsNotAnonMixin,
    SuccessMessageMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    # The model that the permission request is for
    base_model = None
    # The namespace of the app to redirect to
    redirect_namespace = None
    # Checks on whether the permission request user is in these groups
    user_check_attrs = ["is_user", "is_editor"]
    raise_exception = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.base_model is None or self.redirect_namespace is None:
            raise ImproperlyConfigured(
                "`base_model` and `redirect_namespace` must be set."
            )

    @property
    def base_object(self):
        return get_object_or_404(self.base_model, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.base_object

    def form_valid(self, form):
        permission_request = self.get_object()
        user = permission_request.user
        form.instance.user = user
        if not self.base_object.is_editor(self.request.user) and not any(
            getattr(self.base_object, f)(user) for f in self.user_check_attrs
        ):
            form.instance.status = self.model.PENDING
        try:
            redirect = super().form_valid(form)
            return redirect

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "permission_request": self.get_object(),
                "base_object": self.base_object,
            }
        )
        return context

    def get_success_message(self, cleaned_data):
        if not self.base_object.is_editor(self.request.user):
            return "You request for access has been sent to editors"
        return "Permission request successfully updated"

    def get_success_url(self):
        if not self.base_object.is_editor(self.request.user):
            return reverse(f"{self.redirect_namespace}:list")

        return reverse(
            f"{self.redirect_namespace}:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )
