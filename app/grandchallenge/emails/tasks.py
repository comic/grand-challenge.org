from celery import shared_task
from django.contrib.sites.models import Site
from django.core.mail import send_mass_mail
from django.core.paginator import Paginator

from config import settings
from grandchallenge.subdomains.utils import reverse


@shared_task
def send_bulk_email(users, subject, body):
    paginator = Paginator(users, 1000)
    site = Site.objects.get_current()
    messages = []
    for page_nr in paginator.page_range:
        for recipient in paginator.page(page_nr).object_list:
            messages.append(
                (
                    f"[{site.domain.lower()}] {subject}",
                    f"Dear {recipient.username}, "
                    f"\r\n\r\n {body} \r\n\r\n "
                    f"Kind regards, \r\n Grand Challenge team \r\n\r\n "
                    f"To unsubscribe from this mailing list, "
                    f"uncheck 'Receive newsletter' in your profile settings:"
                    f" {reverse('profile-update', kwargs={'username': recipient.username})}",
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient.email],
                )
            )
        send_mass_mail(messages)
