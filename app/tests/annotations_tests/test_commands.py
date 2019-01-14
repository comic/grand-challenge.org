import pytest
from io import StringIO
from django.core.management import call_command, CommandError
from tests.factories import UserFactory


@pytest.mark.django_db
class TestCommands:
    def test_copyannotations_command_requires_arguments(self):
        try:
            call_command("copyannotations")
            assert False
        except CommandError as e:
            assert (
                str(e)
                == "Error: the following arguments are required: user_from, user_to"
            )

    def test_copyannotations_command_invalid_user_from(self):
        non_user = "non_existing_user"
        try:
            call_command("copyannotations", non_user, non_user)
            assert False
        except CommandError as e:
            assert str(e) == "user_from does not exist"

    def test_copyannotations_command_invalid_user_to(self):
        user = UserFactory()
        non_user = "non_existing_user"
        try:
            call_command("copyannotations", user.username, non_user)
            assert False
        except CommandError as e:
            assert str(e) == "user_to does not exist"

    def test_copyannotations_command_no_annotations(self):
        user_from = UserFactory()
        user_to = UserFactory()
        try:
            call_command(
                "copyannotations",
                user_from.username,
                user_to.username,
            )
            assert False
        except CommandError as e:
            assert str(e) == "No annotations found for this user"

    def test_copyannotations_command(self):
        user_from = UserFactory()
        user_to = UserFactory()

        out = StringIO()
        call_command(
            "copyannotations",
            user_from.username,
            user_to.username,
            stdout=out,
        )
        #TODO