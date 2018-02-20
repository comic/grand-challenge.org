import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from social_django.fields import JSONField

from comicsite.core.urlresolvers import reverse
from evaluation.validators import MimeTypeValidator, ExtensionValidator


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


class Config(UUIDModel):
    # This must match the syntax used in jquery datatables
    # https://datatables.net/reference/option/order
    ASCENDING = 'asc'
    DESCENDING = 'desc'
    EVALUATION_SCORE_SORT_CHOICES = (
        (ASCENDING, 'Ascending'),
        (DESCENDING, 'Descending'),
    )

    challenge = models.OneToOneField(
        'comicmodels.ComicSite',
        on_delete=models.CASCADE,
        related_name='evaluation_config',
        editable=False,
    )

    score_jsonpath = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            'The jsonpath of the field in metrics.json that will be used '
            'for the overall scores on the results page. See '
            'http://goessner.net/articles/JsonPath/ for syntax. For example:'
            '\n\ndice.mean'
        ),
    )

    score_title = models.CharField(
        max_length=32,
        blank=False,
        default='Score',
        help_text=(
            'The name that will be displayed for the scores column, for '
            'instance:\n\nScore (log-loss)'
        ),
    )

    score_default_sort = models.CharField(
        max_length=4,
        choices=EVALUATION_SCORE_SORT_CHOICES,
        default=DESCENDING,
        help_text=(
            'The default sorting to use for the scores on the results '
            'page.'
        ),
    )

    extra_results_columns = JSONField(
        default=dict,
        help_text=(
            'A JSON object that contains the extra columns from metrics.json '
            'that will be displayed on the results page. '
            'Where the KEYS contain the titles of the columns, '
            'and the VALUES contain the JsonPath to the corresponding metric '
            'in metrics.json. '
            'For example:\n\n'
            '{"Accuracy": "aggregates.acc","Dice": "dice.mean"}'
        ),
    )

    allow_submission_comments = models.BooleanField(
        default=False,
        help_text=(
            'Allow users to submit comments as part of their submission.'
        ),
    )

    allow_supplementary_file = models.BooleanField(
        default=False,
        help_text=(
            'Show a supplementary file field on the submissions page so that '
            'users can upload an additional file along with their predictions '
            'file as part of their submission (eg, include a pdf description '
            'of their method).'
        ),
    )

    require_supplementary_file = models.BooleanField(
        default=False,
        help_text=(
            'Force users to upload a supplementary file with their '
            'predictions file.'
        ),
    )

    supplementary_file_label = models.CharField(
        max_length=32,
        blank=True,
        default='Supplementary File',
        help_text=(
            'The label that will be used on the submission and results page '
            'for the supplementary file. For example: Algorithm Description.'
        ),
    )

    supplementary_file_help_text = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=(
            'The help text to include on the submissions page to describe the '
            'submissions file. Eg: "A PDF description of the method.".'
        ),
    )

    show_supplementary_file_link = models.BooleanField(
        default=False,
        help_text=(
            'Show a link to download the supplementary file on the results '
            'page.'
        )
    )

    daily_submission_limit = models.PositiveIntegerField(
        default=10,
        help_text=(
            'The limit on the number of times that a user can make a '
            'submission in a 24 hour period.'
        )
    )

    def get_absolute_url(self):
        return reverse('evaluation:manage',
                       kwargs={
                           'challenge_short_name': self.challenge.short_name
                       })


def method_image_path(instance, filename):
    return (
        f'evaluation/'
        f'{instance.challenge.pk}/'
        f'methods/'
        f'{instance.pk}/'
        f'{filename}'
    )


class Method(UUIDModel):
    """
    Stores the methods for performing an evaluation
    """
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                null=True,
                                on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    # Validation for methods needs to be done asynchronously
    ready = models.BooleanField(default=False,
                                editable=False,
                                help_text="Is this method ready to be used?")

    status = models.TextField(editable=False)

    image = models.FileField(
        upload_to=method_image_path,
        validators=[
            ExtensionValidator(
                allowed_extensions=(
                    '.tar',
                )
            ),
        ],
        help_text=(
            'Tar archive of the container '
            'image produced from the command '
            '`docker save IMAGE > '
            'IMAGE.tar`. See '
            'https://docs.docker.com/engine/reference/commandline/save/'
        ),
    )

    image_sha256 = models.CharField(editable=False,
                                    max_length=71)

    def save(self, *args, **kwargs):
        super(Method, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('evaluation:method-detail',
                       kwargs={
                           'pk': self.pk,
                           'challenge_short_name': self.challenge.short_name
                       })


def submission_file_path(instance, filename):
    return (
        f'evaluation/'
        f'{instance.challenge.pk}/'
        f'submissions/'
        f'{instance.creator.pk}/'
        f'{instance.pk}/'
        f'{filename}'
    )


def submission_supplementary_file_path(instance, filename):
    return (
        f'evaluation-supplementary/'
        f'{instance.challenge.pk}/'
        f'{instance.creator.pk}/'
        f'{instance.pk}/'
        f'{filename}'
    )


class Submission(UUIDModel):
    """
    Stores files for evaluation
    """
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                null=True,
                                on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    # Limitation for now: only accept zip files as these are expanded in
    # evaluation.tasks.Evaluation. We could extend this first to csv file
    # submission with some validation
    file = models.FileField(upload_to=submission_file_path,
                            validators=[MimeTypeValidator(
                                allowed_types=('application/zip',))])

    supplementary_file = models.FileField(
        upload_to=submission_supplementary_file_path,
        validators=[
            MimeTypeValidator(allowed_types=(
                'text/plain',
                'application/pdf',
            ))
        ],
        blank=True,
    )

    comment = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text=(
            'You can add a comment here to help you keep track of your '
            'submissions.'
        )
    )

    def get_absolute_url(self):
        return reverse('evaluation:submission-detail',
                       kwargs={
                           'pk': self.pk,
                           'challenge_short_name': self.challenge.short_name
                       })


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

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    submission = models.ForeignKey('Submission',
                                   on_delete=models.CASCADE)

    method = models.ForeignKey('Method',
                               on_delete=models.CASCADE)

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=PENDING)

    status_history = JSONField(default=dict)

    output = models.TextField()

    def clean(self):
        if self.submission.challenge != self.method.challenge:
            raise ValidationError("The submission and method challenges should"
                                  "be the same. You are trying to evaluate a"
                                  f"submission for {self.submission.challenge}"
                                  f"with a method for {self.method.challenge}")
        super(Job, self).clean()

    def save(self, *args, **kwargs):
        self.challenge = self.submission.challenge
        super(Job, self).save(*args, **kwargs)

    def update_status(self, *, status: STATUS_CHOICES, output: str = None):
        self.status = status
        if output:
            self.output = output
        self.save()

    def get_absolute_url(self):
        return reverse('evaluation:job-detail',
                       kwargs={
                           'pk': self.pk,
                           'challenge_short_name': self.challenge.short_name
                       })


class Result(UUIDModel):
    """
    Stores individual results for a challenges
    """

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    job = models.OneToOneField('Job',
                               null=True,
                               on_delete=models.CASCADE)

    metrics = JSONField(default=dict)

    public = models.BooleanField(default=True)

    rank = models.PositiveIntegerField(
        default=0,
        help_text=(
            'The position of this result on the leaderboard. If the value is '
            'zero, then the result is unranked.'
        ),
    )

    # Cache the url as this is slow on the results list page
    absolute_url = models.TextField(
        blank=True,
        editable=False,
    )

    def get_absolute_url(self):
        return reverse('evaluation:result-detail',
                       kwargs={
                           'pk': self.pk,
                           'challenge_short_name': self.challenge.short_name
                       })


def result_screenshot_path(instance, filename):
    return (
        f'evaluation/'
        f'{instance.challenge.pk}/'
        f'screenshots/'
        f'{instance.result.pk}/'
        f'{instance.pk}/'
        f'{filename}'
    )


class ResultScreenshot(UUIDModel):
    """
    Stores a screenshot that is generated during an evaluation
    """
    result = models.ForeignKey('Result',
                               on_delete=models.CASCADE)

    image = models.ImageField(upload_to=result_screenshot_path)
