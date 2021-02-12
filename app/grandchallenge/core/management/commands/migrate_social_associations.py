from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
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

        provider = GmailProvider.id

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for usa in page.object_list:
                SocialAccount.objects.create(
                    user=usa.user, provider=provider, uid=usa.uid,
                )

                # TODO: migrate verified emails elsewhere
                EmailAddress.objects.create(
                    user=usa.user,
                    email=usa.user.email,
                    verified=True,
                    primary=True,
                )
