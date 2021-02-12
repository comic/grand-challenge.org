from datetime import datetime, timedelta

import pytz
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.core.paginator import Paginator
from social_django.models import UserSocialAuth

from grandchallenge.profiles.providers.gmail.provider import GmailProvider


class Command(BaseCommand):
    def handle(self, *args, **options):
        usas = UserSocialAuth.objects.filter(
            provider__exact="google-oauth2"
        ).order_by("id")
        paginator = Paginator(usas, 100)

        print(f"Found {paginator.count} associations")

        adapter = DefaultSocialAccountAdapter()

        provider = GmailProvider.id

        try:
            app = SocialApp.objects.get(provider=provider)
        except ObjectDoesNotExist:
            app = adapter.get_app(request=None, provider=provider)
            app.name = "Gmail Default"
            app.key = ""
            app.save()

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for usa in page.object_list:
                account = SocialAccount.objects.create(
                    user=usa.user, provider=provider, uid=usa.uid,
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

                # TODO: migrate verified emails elsewhere
                EmailAddress.objects.create(
                    user=usa.user,
                    email=usa.user.email,
                    verified=True,
                    primary=True,
                )
