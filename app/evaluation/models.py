import json
import tarfile
import uuid

from django.conf import settings
from django.db import models
from social_django.fields import JSONField

from evaluation.validators import MimeTypeValidator, ContainerImageValidator


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified
    times
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Result(UUIDModel):
    """
    Stores individual results for a challenges
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    metrics = JSONField(default=dict)

    public = models.BooleanField(default=True)


def result_screenshot_path(instance, filename):
    return f'evaluation/{instance.challenge.pk}/screenshots/' \
           f'{instance.result.pk}/{filename}'


class ResultScreenshot(UUIDModel):
    """
    Stores a screenshot that is generated during an evaluation
    """
    result = models.ForeignKey('Result',
                               on_delete=models.CASCADE)

    image = models.ImageField(upload_to=result_screenshot_path)


def method_image_path(instance, filename):
    return f'evaluation/{instance.challenge.pk}/methods/' \
           f'{instance.pk}/{filename}'


class Method(UUIDModel):
    """
    Stores the methods for performing an evaluation
    """
    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True,
                             on_delete=models.SET_NULL)

    image = models.FileField(upload_to=method_image_path,
                             validators=[
                                 MimeTypeValidator(allowed_types=(
                                     'application/x-tarbinary',)),
                                 ContainerImageValidator(single_image=True)],
                             help_text='Tar archive of the container '
                                       'image produced from the command '
                                       '`docker save IMAGE > '
                                       'IMAGE.tar`. See '
                                       'https://docs.docker.com/engine/reference/commandline/save/',
                             )

    # TODO: Add a validator to make sure the form is sha256:{64}
    image_sha256 = models.CharField(editable=False,
                                max_length=71)

    def save(self, *args, **kwargs):
        self.image_sha256 = self._image_sha256
        super(Method, self).save(*args, **kwargs)

    @property
    def _image_sha256(self) -> str:
        with tarfile.open(fileobj=self.image, mode='r') as t:
            member = dict(zip(t.getnames(), t.getmembers()))[
                'manifest.json']
            manifest = t.extractfile(member).read()

        manifest = json.loads(manifest)
        # TODO: Check if the encoding method is included in the manifest
        return f"sha256:{manifest[0]['Config'][:64]}"

    class Meta:
        unique_together = (("challenge", "created"),)


def challenge_submission_path(instance, filename):
    return f'evaluation/{instance.challenge.pk}/submissions/' \
           f'{instance.user.pk}/' \
           f'{instance.created.strftime("%Y%m%d%H%M%S")}/' \
           f'{filename}'


class Submission(UUIDModel):
    """
    Stores files for evaluation
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    # Limitation for now: only accept zip files as these are expanded in
    # evaluation.tasks.Evaluation. We could extend this first to csv file
    # submission with some validation
    file = models.FileField(upload_to=challenge_submission_path,
                            validators=[MimeTypeValidator(
                                allowed_types=('application/zip',))])


class Job(UUIDModel):
    """
    Stores information about a job for a given upload
    """

    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, 'The task is waiting for execution'),
        (STARTED, 'The task has been started'),
        (RETRY, 'The task is to be retried, possibly because of failure'),
        (FAILURE,
         'The task raised an exception, or has exceeded the retry limit'),
        (SUCCESS, 'The task executed successfully'),
        (CANCELLED, 'The task was cancelled')
    )

    submission = models.ForeignKey('Submission',
                                   null=True,
                                   on_delete=models.SET_NULL)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=PENDING)

    status_history = JSONField(default=dict)

    output = models.TextField()

    def update_status(self, *, status: STATUS_CHOICES, output: str=None):
        self.status = status
        if output:
            self.output=output
        self.save()


class StagedFile(models.Model):
    """
    Files uploaded but not committed to other forms.
    """
    csrf = models.CharField(max_length=128)
    client_id = models.CharField(max_length=128, null=True)
    client_filename = models.CharField(max_length=128, blank=False)

    file_id = models.UUIDField(blank=False)
    timeout = models.DateTimeField(blank=False)

    file = models.FileField(blank=False)
    start_byte = models.BigIntegerField(blank=False)
    end_byte = models.BigIntegerField(blank=False)
    total_size = models.BigIntegerField(null=True)
