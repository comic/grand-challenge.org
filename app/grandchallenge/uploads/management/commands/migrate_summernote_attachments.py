from os.path import basename

from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.management import BaseCommand

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
            old_path = attachment.file.name
            filename = basename(old_path)
            new_path = upload_to(attachment.file, filename)

            if old_storage.exists(
                old_path
            ) and not attachment.file.storage.exists(new_path):
                old_f = File(old_storage.open(old_path))
                attachment.file.save(filename, old_f)
