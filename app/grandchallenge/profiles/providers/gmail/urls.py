from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from grandchallenge.profiles.providers.gmail.provider import GmailProvider

urlpatterns = default_urlpatterns(GmailProvider)
