from datetime import datetime, timezone

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import base36_to_int


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    # Timestamps are relative to this, see PasswordResetTokenGenerator
    epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.verification.email_is_verified}"

    def get_timestamp(self, token):
        ts_b36, _ = token.split("-")
        ts = base36_to_int(ts_b36)
        return ts + self.epoch

    def _num_seconds(self, dt):
        return int((dt - self.epoch).total_seconds())


email_verification_token_generator = EmailVerificationTokenGenerator()
