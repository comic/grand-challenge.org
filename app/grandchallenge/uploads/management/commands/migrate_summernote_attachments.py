from os.path import basename

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management import BaseCommand

from grandchallenge.pages.models import Page
from grandchallenge.uploads.models import (
    SummernoteAttachment,
    summernote_upload_filepath,
)


class Command(BaseCommand):
    def handle(self, *args, **options):
        attachments = SummernoteAttachment.objects.all()
        old_storage = FileSystemStorage()
        # There doesn't seem a good way to get the upload_to from the file
        # field, so explicitly do it here
        upload_to = summernote_upload_filepath

        for attachment in attachments:
            filefield = attachment.file
            old_url = f"{settings.MEDIA_URL}{filefield.name}"
            filename = basename(filefield.name)
            new_path = upload_to(attachment, filename)

            if old_storage.exists(
                filefield.name
            ) and not filefield.storage.exists(new_path):
                print(f"Migrating {filefield.url}")
                filefield.save(
                    filename, File(old_storage.open(filefield.name))
                )

                for p in Page.objects.filter(html__contains=old_url):
                    print(
                        f"Updating {filefield.url} in {p.get_absolute_url()}"
                    )
                    p.html = p.html.replace(old_url, filefield.url)
                    p.save()

            else:
                print(f"Not migrating {filefield.url}")
