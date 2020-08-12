from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail


def send_failed_file_import(n_errors, upload_session):
    subject = f"[{Site.objects.get_current().domain.lower()}] "
    object_msg = ""

    if upload_session.reader_study:
        subject += f"[{upload_session.reader_study.title.lower()}] "
        object_msg = f"for reader study {upload_session.reader_study}"

    if upload_session.archive:
        subject += f"[{upload_session.archive.title.lower()}]"
        object_msg = f"for archive {upload_session.archive.title}"

    if (
        upload_session.algorithm_image
        and upload_session.algorithm_image.algorithm
    ):
        subject += (
            f"[{upload_session.algorithm_image.algorithm.title.lower()}] "
        )
        object_msg = (
            f"for algorithm {upload_session.algorithm_image.algorithm}"
        )

    msg = (
        f"{n_errors} image files could not be processed "
        f"{object_msg}."
        "The following file formats are supported: "
        ".mha, .mhd, .raw, .zraw, .dcm, .nii, .nii.gz, .tiff, .png, .jpeg and .jpg. "
        f"Please see {upload_session.get_absolute_url()} for more information."
    )

    send_mail(
        subject=subject + " Unable to import images",
        message=msg,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[upload_session.creator.email],
    )
