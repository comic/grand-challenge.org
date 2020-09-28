from django.urls import path, re_path

from grandchallenge.verifications.views import (
    ConfirmEmailView,
    VerificationCreate,
    VerificationDetail,
)

app_name = "verifications"

urlpatterns = [
    path("create/", VerificationCreate.as_view(), name="create"),
    path("confirm/<token>/", ConfirmEmailView.as_view(), name="confirm"),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/$",
        VerificationDetail.as_view(),
        name="detail",
    ),
]
