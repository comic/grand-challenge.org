from django.db import models


class Email(models.Model):

    subject = models.CharField(max_length=1024)
    body = models.TextField(
        help_text="Email body will be prepended with 'Dear [username],' and will end with 'Kind regards, Grand Challenge team' and a link to unsubscribe from the mailing list."
    )
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.subject
