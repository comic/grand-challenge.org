from django.db import models


class SendActionChoices(models.TextChoices):
    MAILING_LIST = "send_to_mailing_list"
    STAFF = "send_to_staff"
    CHALLENGE_ADMINS = "send_to_challenge_admins"
    READER_STUDY_EDITORS = "send_to_readerstudy_editors"
    ALGORITHM_EDITORS = "send_to_algorithm_editors"
