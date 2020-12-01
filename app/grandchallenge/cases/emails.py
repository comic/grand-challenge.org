from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail


def send_failed_file_import(n_errors, upload_session):
    subject = f"[{Site.objects.get_current().domain.lower()}] Unable to import images"

    msg = (
        f"In your recent upload, {n_errors} image files could not be processed."
        "The following file formats are supported: "
        ".mha, .mhd, .raw, .zraw, .dcm, .nii, .nii.gz, .tiff, .png, .jpeg and .jpg. "
        f"Please see {upload_session.get_absolute_url()} for more information."
    )

    send_mail(
        subject=subject,
        message=msg,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[upload_session.creator.email],
    )
