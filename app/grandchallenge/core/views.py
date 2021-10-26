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
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.blogs.models import Post
from grandchallenge.challenges.models import Challenge
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
                    "Objectively assess the performance of algorithms",
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
            Highlight(
                title="Find Certified Solutions",
                bullet_points=[
                    "Filter to easily find solutions to your clinical questions",
                    "Compare product specifications",
                    "Verify CE and FDA certification",
                ],
                url=reverse("products:product-list"),
                url_title="Products",
                image="images/products.png",
            ),
        ]

        latest_news_item = Post.objects.filter(
            published=True, highlight=True
        ).first()
        latest_ai_for_radiology_post = Post.objects.filter(
            published=True, tags__slug="products"
        ).first()
        latest_gc_blog_post = (
            Post.objects.filter(published=True)
            .exclude(tags__slug="products")
            .exclude(highlight=True)
            .first()
        )
        news_caroussel_items = [
            item
            for item in [
                latest_news_item,
                latest_ai_for_radiology_post,
                latest_gc_blog_post,
            ]
            if item
        ]

        context.update(
            {
                "all_users": get_user_model().objects.all(),
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
                .prefetch_related("publications",)
                .order_by("-created")
                .all()[:4],
                "news_caroussel_items": news_caroussel_items,
                "latest_news_item": latest_news_item,
            }
        )
        return context


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
