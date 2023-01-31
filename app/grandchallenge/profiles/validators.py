from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


def username_is_not_email(username):
    try:
        EmailValidator()(username)
    except ValidationError:
        # Username is not an email address
        pass
    else:
        raise ValidationError("You cannot use an email address as a username")


username_validators = [username_is_not_email, UnicodeUsernameValidator()]
