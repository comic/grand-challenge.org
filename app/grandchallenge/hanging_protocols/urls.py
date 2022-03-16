from django.urls import path

from grandchallenge.hanging_protocols.views import (
    HangingProtocolCreate,
    HangingProtocolDetail,
    HangingProtocolList,
    HangingProtocolUpdate,
)

app_name = "hanging-protocols"

urlpatterns = [
    path("", HangingProtocolList.as_view(), name="list"),
    path("create/", HangingProtocolCreate.as_view(), name="create"),
    path("<slug:slug>/", HangingProtocolDetail.as_view(), name="detail"),
    path("<slug>/update/", HangingProtocolUpdate.as_view(), name="update"),
]
