from datetime import datetime, timedelta

import pytz
import requests
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.providers.google.provider import GoogleProvider
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.core.paginator import Paginator
from social_django.models import UserSocialAuth


class Command(BaseCommand):
    def handle(self, *args, **options):
        usas = UserSocialAuth.objects.filter(
            provider__exact="google-oauth2"
        ).order_by("id")
        paginator = Paginator(usas, 100)

        print(f"Found {paginator.count} associations")

        adapter = DefaultSocialAccountAdapter()

        try:
            app = SocialApp.objects.get(provider=GoogleProvider.id)
        except ObjectDoesNotExist:
            app = adapter.get_app(request=None, provider=GoogleProvider.id)
            app.name = "Google default"
            app.key = ""
            app.save()

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for usa in page.object_list:
                # TODO: we need to fetch the profile id to set the uid to SocialAccount, but dsa uses email
                resp = requests.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    params={
                        "access_token": usa.extra_data["access_token"],
                        "alt": "json",
                    },
                )
                resp.raise_for_status()
                extra_data = resp.json()

                account = SocialAccount.objects.create(
                    user=usa.user,
                    provider=GoogleProvider.id,
                    uid=extra_data["id"],
                    extra_data=extra_data,
                )

                SocialToken.objects.create(
                    app=app,
                    account=account,
                    token=usa.extra_data["access_token"],
                    expires_at=datetime.fromtimestamp(
                        usa.extra_data["auth_time"], tz=pytz.UTC
                    )
                    + timedelta(seconds=usa.extra_data["expires"]),
                )

                if extra_data["verified_email"]:
                    # TODO: migrate verified emails elsewhere
                    EmailAddress.objects.create(
                        user=usa.user,
                        email=extra_data["email"],
                        verified=True,
                        primary=True,
                    )
