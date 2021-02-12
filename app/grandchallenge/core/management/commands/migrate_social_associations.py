from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.core.paginator import Paginator
from social_django.models import UserSocialAuth

from grandchallenge.profiles.providers.gmail.provider import GmailProvider


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.migrate_emails()
        self.migrate_auths()

    def migrate_auths(self):
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

    def migrate_emails(self):
        """Emails from active users have previously been verified"""
        users = get_user_model().objects.filter(is_active=True).order_by("id")
        paginator = Paginator(users, 100)

        print(f"Found {paginator.count} users")

        for idx in paginator.page_range:
            print(f"Page {idx} of {paginator.num_pages}")

            page = paginator.page(idx)

            for user in page.object_list:
                if user.email:
                    EmailAddress.objects.create(
                        user=user,
                        email=user.email,
                        verified=True,
                        primary=True,
                    )
