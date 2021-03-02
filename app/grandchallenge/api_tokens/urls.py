from django.urls import path

from grandchallenge.api_tokens.views import APITokenList

app_name = "api-tokens"

urlpatterns = [path("", APITokenList.as_view(), name="list")]
