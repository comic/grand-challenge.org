from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)

from grandchallenge.profiles.providers.gmail.provider import GmailProvider


class GmailOAuth2Adapter(GoogleOAuth2Adapter):
    provider_id = GmailProvider.id


oauth2_login = OAuth2LoginView.adapter_view(GmailOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(GmailOAuth2Adapter)
