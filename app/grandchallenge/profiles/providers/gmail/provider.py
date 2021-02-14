from allauth.socialaccount.providers.google.provider import GoogleProvider


class GmailProvider(GoogleProvider):
    id = "gmail"
    name = "Google"

    def extract_uid(self, data):
        return str(data["email"])


provider_classes = [GmailProvider]
