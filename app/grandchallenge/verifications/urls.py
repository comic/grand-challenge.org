from django.urls import path, re_path

from grandchallenge.verifications.views import (
    VerificationCreate,
    VerificationDetail,
)

app_name = "verifications"

urlpatterns = [
    path("create/", VerificationCreate.as_view(), name="create"),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/$",
        VerificationDetail.as_view(),
        name="detail",
    ),
]
