from allauth.socialaccount.providers.google.provider import GoogleProvider

from grandchallenge.profiles.providers.gmail.views import GmailOAuth2Adapter


class GmailProvider(GoogleProvider):
    id = "gmail"
    name = "Google"
    oauth2_adapter_class = GmailOAuth2Adapter

    def extract_uid(self, data):
        return str(data["email"])


provider_classes = [GmailProvider]
