from django.urls import path

from grandchallenge.api_tokens.views import APITokenCreate, APITokenList

app_name = "api-tokens"

urlpatterns = [
    path("", APITokenList.as_view(), name="list"),
    path("create/", APITokenCreate.as_view(), name="create"),
]
