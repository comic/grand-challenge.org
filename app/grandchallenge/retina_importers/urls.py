from django.urls import path

from grandchallenge.retina_importers import views

app_name = "importers"

urlpatterns = [
    path("check_image/", views.CheckImage.as_view(), name="check-image"),
    path("upload_image/", views.UploadImage.as_view(), name="upload-image"),
]
