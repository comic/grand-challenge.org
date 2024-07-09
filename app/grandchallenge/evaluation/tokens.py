from django.contrib.auth.tokens import PasswordResetTokenGenerator


class ExternalEvaluationTokenGenerator(PasswordResetTokenGenerator):

    def _make_hash_value(self, user, timestamp):
        state_dict = user
        return (
            f"{state_dict['user'].pk}"
            f"{timestamp}"
            f"{state_dict['evaluation'].status}"
            f"{state_dict['evaluation'].outputs.all()}"
            f"{state_dict['evaluation'].error_message}"
        )


external_evaluation_token_generator = ExternalEvaluationTokenGenerator()
