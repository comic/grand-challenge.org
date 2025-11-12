from dataclasses import dataclass
from random import choice

from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.forms.utils import ErrorList
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.templatetags.static import static
from django.views import View
from django.views.generic import TemplateView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.blogs.models import Post
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy


@dataclass
class Highlight:
    title: str
    image: str
    url: str
    url_title: str
    description: str = ""
    bullet_points: list = list


class HomeTemplate(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        background_url = static(
            choice(
                [
                    "images/pathology_banner.jpg",
                    "images/ophthalmology_banner.png",
                    "images/radiology_banner_1.png",
                    "images/radiology_banner_2.png",
                ]
            )
        )

        highlights = [
            Highlight(
                title="Manage Your Data",
                bullet_points=[
                    "Upload medical imaging data easily and securely",
                    "Control who has access to the data",
                    "View data with our globally available browser-based workstations",
                ],
                url=reverse("archives:list"),
                url_title="Archives",
                image="images/archive.png",
            ),
            Highlight(
                title="Train Expert Annotators",
                bullet_points=[
                    "Create sets of questions that users must answer about a dataset",
                    "Invite clinical experts take part in the training",
                    "Deliver immediate feedback on performance",
                ],
                url=reverse("reader-studies:list"),
                url_title="Courses",
                image="images/education.png",
            ),
            Highlight(
                title="Gather Annotations",
                bullet_points=[
                    "Create your own set of questions for your dataset",
                    "Customise the hanging protocols and overlays",
                    "Use our intuitive workstations to view and report the images",
                ],
                url=reverse("reader-studies:list"),
                url_title="Reader Studies",
                image="images/annotation.png",
            ),
            Highlight(
                title="Benchmark Algorithms",
                bullet_points=[
                    "Manage your annotated training, test and validation data sets",
                    "Gather machine learning solutions for your clinical question",
                    "Fair assessment of algorithm performance",
                ],
                url=reverse("challenges:list"),
                url_title="Challenges",
                image="images/challenge.png",
            ),
            Highlight(
                title="Deploy Your Algorithms",
                bullet_points=[
                    "Upload algorithm container images",
                    "Manage access for clinical and non-clinical researchers",
                    "Upload data for execution by your algorithm on our infrastructure",
                ],
                url=reverse("algorithms:list"),
                url_title="Algorithms",
                image="images/algorithms.png",
            ),
        ]

        news_carousel_items = Post.objects.filter(
            published=True, highlight=True
        ).order_by("-created")[:3]

        context.update(
            {
                "all_users": get_user_model().objects.filter(
                    is_active=True, last_login__isnull=False
                ),
                "all_challenges": Challenge.objects.all(),
                "all_algorithms": Algorithm.objects.all(),
                "highlights": highlights,
                "jumbotron_background_url": background_url,
                "jumbotron_title": "Grand Challenge",
                "jumbotron_description": (
                    "A platform for end-to-end development of machine "
                    "learning solutions in biomedical imaging."
                ),
                "highlighted_challenges": Challenge.objects.filter(
                    hidden=False, highlight=True
                )
                .prefetch_related("phase_set", "publications")
                .order_by("-created")
                .all()[:4],
                "highlighted_algorithms": Algorithm.objects.filter(
                    public=True, highlight=True
                )
                .prefetch_related("publications")
                .order_by("-created")
                .all()[:4],
                "news_carousel_items": news_carousel_items,
            }
        )
        return context


class ChallengeSuspendedView(TemplateView):
    template_name = "challenge_suspended.html"


class PermissionRequestUpdate(
    LoginRequiredMixin,
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
    login_url = reverse_lazy("account_login")

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
            form.add_error(None, ErrorList(e.messages))
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
            return "Your request for access has been sent to the editors"
        return "Permission request successfully updated"

    def get_success_url(self):
        if not self.base_object.is_editor(self.request.user):
            return reverse(f"{self.redirect_namespace}:list")

        return reverse(
            f"{self.redirect_namespace}:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )


def healthcheck(request):
    return HttpResponse("")


class RedirectPath(View):
    """Redirects all sub-paths to a different domain."""

    netloc = None
    permanent = False

    def get(self, request, *args, path="", **kwargs):
        if self.netloc is None:
            raise ImproperlyConfigured("`netloc` must be set.")

        return redirect(
            f"https://{self.netloc}/{path}", permanent=self.permanent
        )


def handler403(request, exception):
    request.challenge = None
    content = loader.render_to_string(
        template_name="403.html", request=request
    )
    return HttpResponseForbidden(content)


def handler404(request, exception):
    request.challenge = None
    content = loader.render_to_string(
        template_name="404.html", request=request
    )
    return HttpResponseNotFound(content)


def handler500(request):
    request.challenge = None
    content = loader.render_to_string(
        template_name="500.html", request=request
    )
    return HttpResponseServerError(content)


class GracefulPaginator(Paginator):
    def page(self, number):
        """
        Always return a valid page number rather than raising 404s

        Could be bad for SEO, so only use on private ListViews.
        See https://forum.djangoproject.com/t/letting-listview-gracefully-handle-out-of-range-page-numbers/23037/3
        """
        try:
            number = self.validate_number(number)
        except PageNotAnInteger:
            number = 1
        except EmptyPage:
            number = self.num_pages
        return super().page(number)
