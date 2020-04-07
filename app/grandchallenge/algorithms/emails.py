from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.evaluation.templatetags.evaluation_extras import user_error


def send_failed_job_email(job):
    algorithm = job.algorithm_image.algorithm
    message = (
        f"Unfortunately your job for algorithm "
        f"'{algorithm.title}' failed with an error. "
        f"The error message is:\n\n"
        "{}\n\n"
        f"You may wish to try and correct this, or contact the algorithm "
        f"editors. The following information may help them:\n"
        f"User: {job.creator.username}\n"
        f"Job ID: {job.pk}\n"
        f"Submission ID: {job.pk}"
    )

    emails = {job.creator.email: message.format(user_error(job.output))}
    emails.update(
        {
            o.email: message.format(job.output)
            for o in algorithm.editors_group.user_set.all()
        }
    )

    for email, message in emails.items():
        send_mail(
            subject=(
                f"[{Site.objects.get_current().domain.lower()}] "
                f"[{algorithm.title.lower()}] "
                f"Job Failed"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
