from django.conf import settings
from django.db import models

from challenges.models import Challenge


class RegistrationRequest(models.Model):
    """
    When a user wants to join a project, admins have the option of reviewing
    each user before allowing or denying them. This class records the needed
    info for that.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="which user requested to participate?",
    )
    challenge = models.ForeignKey(
        Challenge, help_text="To which project does the user want to register?"
    )
    created = models.DateTimeField(auto_now_add=True)
    changed = models.DateTimeField(auto_now=True)
    PENDING = 'PEND'
    ACCEPTED = 'ACPT'
    REJECTED = 'RJCT'
    REGISTRATION_CHOICES = (
        (PENDING, 'Pending'), (ACCEPTED, 'Accepted'), (REJECTED, 'Rejected')
    )
    status = models.CharField(
        max_length=4, choices=REGISTRATION_CHOICES, default=PENDING
    )

    # question: where to send email to admin? probably not here?
    def __str__(self):
        """ describes this object in admin interface etc.
        """
        return "{1} registration request by user {0}".format(
            self.user.username, self.challenge.short_name
        )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def status_to_string(self):
        status = (
            f"Your request to join {self.challenge.short_name}, "
            f"sent {self.format_date(self.created)}"
        )
        if self.status == self.PENDING:
            status += ", is awaiting review"
        elif self.status == self.ACCEPTED:
            status += ", was accepted at " + self.format_date(self.changed)
        elif self.status == self.REJECTED:
            status += ", was rejected at " + self.format_date(self.changed)
        return status

    @staticmethod
    def format_date(date):
        return date.strftime('%b %d, %Y at %H:%M')

    def user_affiliation(self):
        profile = self.user.user_profile
        return profile.institution + " - " + profile.department

    class Meta:
        unique_together = (('challenge', 'user'),)
