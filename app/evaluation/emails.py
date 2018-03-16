import json

from django.conf import settings
from django.core.mail import send_mail

from comicsite.core.urlresolvers import reverse
from evaluation.models import Result, Job


def send_failed_job_email(job: Job):
    message = (
        f'Unfortunately the evaluation for the submission to '
        f'{job.challenge.short_name} failed with an error. The error message '
        f'is:\n\n'
        f'{job.output}\n\n'
        f'You may wish to try and correct this, or contact the challenge '
        f'organizers. The following information may help them:\n'
        f'User: {job.submission.creator.username}\n'
        f'Job ID: {job.pk}\n'
        f'Submission ID: {job.submission.pk}'
    )

    recipient_list = [o.email for o in job.challenge.get_admins()]
    recipient_list.append(job.submission.creator.email)

    for r in recipient_list:
        send_mail(
            subject='Evaluation Failed',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[r.email],
        )


def send_new_result_email(result: Result):
    recipient_list = [o.email for o in result.challenge.get_admins()]

    message = (
        f'There is a new result for {result.challenge.short_name} from '
        f'{result.job.submission.creator.username}. The following metrics '
        f'were calculated:\n\n'
        f'{json.dumps(result.metrics, indent=2)}\n\n'
    )

    if result.public:
        leaderboard_url = reverse(
            'evaluation:results-list',
            kwargs={
                'challenge_short_name': result.challenge.short_name,
            }
        )

        message += (
            f'You can view the result on the leaderboard here: '
            f'{leaderboard_url}'
        )

        recipient_list.append(result.job.submission.creator.email)
    else:
        message += (
            f'You can publish the result on the leaderboard here: '
            f'{result.get_absolute_url()}'
        )

    for r in recipient_list:
        send_mail(
            subject=f'New Result for {result.challenge.short_name}',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[r.email],
        )
