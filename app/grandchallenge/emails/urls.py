from django.urls import path

from grandchallenge.emails.views import EmailCreate, EmailDetail, EmailUpdate

app_name = "emails"

urlpatterns = [
    path("create/", EmailCreate.as_view(), name="create"),
    path("<int:pk>/", EmailDetail.as_view(), name="detail"),
    path("<int:pk>/update/", EmailUpdate.as_view(), name="update"),
]
