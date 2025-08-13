import datetime
import re
from random import choice

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils.crypto import get_random_string

from grandchallenge.challenges.models import Challenge
from grandchallenge.pages.models import Page
from grandchallenge.profiles.models import NotificationEmailOptions
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.factories import (
    PageFactory,
    RegistrationRequestFactory,
    UserFactory,
)
from tests.utils import get_http_host

PI_LINE_END_REGEX = "(\r\n|\n)"


def create_page(
    challenge, title, content="testcontent", permission_level=None
):
    if permission_level is None:
        permission_level = Page.ALL
    return PageFactory(
        display_title=title,
        challenge=challenge,
        content_markdown=content,
        permission_level=permission_level,
    )


class GrandChallengeFrameworkTestCase(TestCase):
    def setUp(self):
        self._create_root_superuser()
        [
            self.testchallenge,
            self.root,
            self.challengeadmin,
            self.participant,
            self.registered_user,
        ] = self._create_dummy_project("test-project")

    def _create_root_superuser(self):
        self.root = UserFactory(
            username="root",
            email="test@test.com",
            is_active=True,
            is_superuser=True,
        )

        EmailAddress.objects.create(
            user=self.root, email=self.root.email, verified=True
        )

    def _create_dummy_project(self, projectname="testproject"):
        """Create a test challenge with some pages and some site users."""
        # Create three types of users:
        # Root = superuser, can do anything,
        root = self.root
        # A user who has created a challenge
        challengeadmin = self._create_random_user("projectadmin")
        testchallenge = self._create_challenge_in_admin(
            challengeadmin, projectname
        )
        create_page(testchallenge, "testpage1")
        create_page(testchallenge, "testpage2")
        # a user who registered for the challenge and was accepted
        participant = self._create_random_user("participant")
        self._register(participant, testchallenge)
        # a user who only signed up to website but did not register to any challenge
        registered_user = self._create_random_user("registered")
        return [
            testchallenge,
            root,
            challengeadmin,
            participant,
            registered_user,
        ]

    def _register(self, user, challenge):
        """
        Register user for the given challenge, follow actual signup as closely
        as possible.
        """
        request = RegistrationRequestFactory(challenge=challenge, user=user)
        request.status = request.ACCEPTED
        request.save()
        assert challenge.is_participant(user)

    def _test_page_can_be_viewed(self, user, page):
        page_url = reverse(
            "pages:detail",
            kwargs={
                "challenge_short_name": page.challenge.short_name,
                "slug": page.slug,
            },
        )
        return self._test_url_can_be_viewed(user, page_url)

    def _test_page_can_not_be_viewed(self, user, page):
        page_url = reverse(
            "pages:detail",
            kwargs={
                "challenge_short_name": page.challenge.short_name,
                "slug": page.slug,
            },
        )
        return self._test_url_can_not_be_viewed(user, page_url)

    def _test_url_can_be_viewed(self, user, url):
        response, username = self._view_url(user, url)
        self.assertEqual(
            response.status_code,
            200,
            "could not load page"
            "'%s' logged in as user '%s'. Expected HTML200, got HTML%s"
            % (url, user, str(response.status_code)),
        )
        return response

    def _test_url_can_not_be_viewed(self, user, url):
        response, username = self._view_url(user, url)
        self.assertNotEqual(
            response.status_code,
            200,
            "could load restricted "
            "page'%s' logged in as user '%s'" % (url, username),
        )
        return response

    def _view_url(self, user, url):
        self.client.logout()

        if user is not None:
            self.client.force_login(user)

        url, kwargs = get_http_host(url=url, kwargs={})

        response = self.client.get(url, **kwargs)

        if user is None:
            username = "anonymous_user"
        else:
            username = user.username

        return response, username

    def _signup_user(self, override):
        """Create a user in the same way as a new user is signed up on the project.
        any key specified in data overwrites default key passed to form.
        For example, signup_user({'username':'user1'}) to creates a user called
        'user1' and fills the rest with default data.
        """
        password = get_random_string(32)

        data = {
            "first_name": "test",
            "last_name": "test",
            "username": "test",
            "email": "test@test.com",
            "email2": "test@test.com",
            "password1": password,
            "password2": password,
            "institution": "test",
            "department": "test",
            "country": "NL",
            "website": "https://www.example.com",
            "only_account": True,
            "notification_email_choice": NotificationEmailOptions.DAILY_SUMMARY,
        }
        data.update(override)

        self.client.logout()

        response = self.client.post(
            reverse("account_signup"), data, follow=True
        )

        assert response.status_code == 200
        assert response.template_name == ["account/verification_sent.html"]

        assert get_user_model().objects.get(username=data["username"])

    def _create_random_user(self, startname=""):
        username = startname + "".join(
            [choice("AEOUY") + choice("QWRTPSDFGHHKLMNB") for x in range(3)]
        )
        data = {
            "username": username,
            "email": username + "@test.com",
            "email2": username + "@test.com",
        }
        return self._create_user(data)

    def _create_user(self, data):
        """
        Sign up user in a way as close to production as possible.

        Check a lot of stuff. Data is a dictionary form_field:for_value pairs.
        Any unspecified values are given default values.
        """
        username = data["username"]

        self._signup_user(data)

        validation_mail = [
            e
            for e in mail.outbox
            if {r.casefold() for r in e.recipients()}
            == {data["email"].casefold()}
        ][0]

        self.assertTrue(
            "Please Confirm Your Email Address" in validation_mail.subject,
            "There was no email sent which had 'Please Confirm Your Email Address' "
            "in the subject line",
        )
        # validate the user with the link that was emailed
        pattern = "/testserver(.*)" + PI_LINE_END_REGEX
        validationlink_result = re.search(
            pattern, validation_mail.body, re.IGNORECASE
        )
        self.assertTrue(
            validationlink_result,
            "could not find any link in"
            "registration email. Tried to match pattern '{}' but found no match in"
            "this email: {}{}".format(
                pattern, PI_LINE_END_REGEX, validation_mail.body
            ),
        )
        validationlink = validationlink_result.group(1).strip()
        response = self.client.post(validationlink, follow=True)
        self.assertEqual(
            response.status_code,
            200,
            "Could not load user validation link. Expected"
            " a redirect (HTTP 200), got HTTP {} instead".format(
                response.status_code
            ),
        )
        resp = self.client.get("/users/" + username + "/")
        self.assertEqual(
            resp.status_code,
            200,
            "Could not access user account after using"
            "validation link! Expected 200, got {} instead".format(
                resp.status_code
            ),
        )
        User = get_user_model()  # noqa: N806
        query_result = User.objects.filter(username=username)
        return query_result[0]

    def _try_create_challenge_request(
        self, user, short_name, title="test project"
    ):
        url = reverse("challenges:requests-create")
        data = {
            "creator": user,
            "title": title,
            "short_name": short_name,
            "contact_email": user.email,
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=1),
            "expected_number_of_participants": 10,
            "abstract": "test",
            "organizers": "test",
            "challenge_setup": "test",
            "data_set": "test",
            "submission_assessment": "test",
            "challenge_publication": "test",
            "code_availability": "test",
            "expected_number_of_teams": 10,
            "number_of_tasks": 1,
        }

        self.client.force_login(user)
        response = self.client.post(url, data)

        return response

    def _create_challenge_in_admin(
        self, user, short_name, description="test project"
    ):
        """Create a challenge object as if created through django admin interface."""
        Verification.objects.create(user=user, is_verified=True)
        challenge = Challenge.objects.create(
            creator=user, short_name=short_name, description=description
        )
        return challenge


class CreateChallengeRequestTest(GrandChallengeFrameworkTestCase):
    def test_cannot_create_request_with_weird_name(self):
        # A user who has created a project
        self.projectadmin = self._create_random_user("projectadmin")
        Verification.objects.create(
            user=self.projectadmin,
            is_verified=True,
            email=self.projectadmin.email,
        )

        challenge_short_name = "under_score"
        response = self._try_create_challenge_request(
            self.projectadmin, challenge_short_name
        )
        assert "Underscores (_) are not allowed." in response.rendered_content

        challenge_short_name = "project with spaces"
        response = self._try_create_challenge_request(
            self.projectadmin, challenge_short_name
        )
        assert (
            "Enter a valid “slug” consisting of letters, numbers, underscores or hyphens"
            in response.rendered_content
        )

        challenge_short_name = "project-with-w#$%^rd-items"
        response = self._try_create_challenge_request(
            self.projectadmin, challenge_short_name
        )
        assert (
            "Enter a valid “slug” consisting of letters, numbers, underscores or hyphens"
            in response.rendered_content
        )

        challenge_short_name = "images"
        response = self._try_create_challenge_request(
            self.projectadmin, challenge_short_name
        )
        assert "That name is not allowed." in response.rendered_content


class ViewsTest(GrandChallengeFrameworkTestCase):
    def test_page_view_permission(self):
        """
        Check that a page with permissions set can only be viewed by the
        correct users.
        """
        adminonlypage = create_page(
            self.testchallenge,
            "adminonlypage",
            permission_level=Page.ADMIN_ONLY,
        )
        registeredonlypage = create_page(
            self.testchallenge,
            "registeredonlypage",
            permission_level=Page.REGISTERED_ONLY,
        )
        publicpage = create_page(
            self.testchallenge, "publicpage", permission_level=Page.ALL
        )
        self._test_page_can_be_viewed(self.challengeadmin, adminonlypage)
        self._test_page_can_not_be_viewed(self.participant, adminonlypage)
        self._test_page_can_not_be_viewed(self.registered_user, adminonlypage)
        self._test_page_can_not_be_viewed(
            None, adminonlypage
        )  # None = not logged in
        self._test_page_can_be_viewed(self.challengeadmin, registeredonlypage)
        self._test_page_can_be_viewed(self.participant, registeredonlypage)
        self._test_page_can_not_be_viewed(
            self.registered_user, registeredonlypage
        )
        self._test_page_can_not_be_viewed(
            None, registeredonlypage
        )  # None = not logged in
        self._test_page_can_be_viewed(self.challengeadmin, publicpage)
        self._test_page_can_be_viewed(self.participant, publicpage)
        self._test_page_can_be_viewed(self.registered_user, publicpage)
        self._test_page_can_be_viewed(None, publicpage)  # None = not logged in

    def test_robots_txt_can_be_loaded(self):
        """Check there are no errors in finding robots.txt."""
        # main domain robots.txt
        robots_url = "/robots.txt"
        robots_url_project = reverse(
            "well_known:robots_txt",
            kwargs={"challenge_short_name": self.testchallenge.short_name},
        )
        self._test_url_can_be_viewed(None, robots_url)  # None = not logged in
        self._test_url_can_be_viewed(
            None, robots_url_project
        )  # None = not logged in

    def test_non_exitant_page_gives_404(self):
        """Reproduces https://github.com/comic/grand-challenge.org/issues/219."""
        page_url = reverse(
            "pages:detail",
            kwargs={
                "challenge_short_name": self.testchallenge.short_name,
                "slug": "doesnotexistpage",
            },
        )
        response, username = self._view_url(None, page_url)
        self.assertEqual(
            response.status_code,
            404,
            "Expected non existing page"
            "'%s' to give 404, instead found %s"
            % (page_url, response.status_code),
        )

    def test_non_exitant_project_gives_404(self):
        """Reproduces https://github.com/comic/grand-challenge.org/issues/219."""
        non_existant_url = reverse(
            "pages:home", kwargs={"challenge_short_name": "nonexistingproject"}
        )
        response, username = self._view_url(None, non_existant_url)

        # We redirect to the main challenge if it is not found
        self.assertEqual(
            response.status_code,
            404,
            "Expected non existing url"
            "'%s' to give 404, instead found %s"
            % (non_existant_url, response.status_code),
        )


class ProjectLoginTest(GrandChallengeFrameworkTestCase):
    """
    Tests the general login and logout views,
    as well as the challenge specific sign-up view.
    """

    def test_project_login(self):
        login_url = reverse("account_login")
        logout_url = reverse("account_logout")
        profile_signup_complete_url = reverse(
            "profile-detail",
            kwargs={"username": self.registered_user.username},
        )
        challenge_sign_up_url = reverse(
            "participants:registration-create",
            kwargs={"challenge_short_name": self.testchallenge.short_name},
        )

        # login page
        self._test_url_can_be_viewed(None, login_url)
        self._test_url_can_not_be_viewed(self.registered_user, login_url)

        # logout page
        self._test_url_can_not_be_viewed(None, logout_url)
        self._test_url_can_be_viewed(self.registered_user, logout_url)

        # profile sign up complete page
        self._test_url_can_be_viewed(
            self.registered_user, profile_signup_complete_url
        )
        self._test_url_can_be_viewed(None, profile_signup_complete_url)

        # password reset is in the "forgot password?" link
        self._test_url_can_be_viewed(
            self.registered_user, reverse("account_reset_password")
        )

        # challenge sign up page
        self._test_url_can_be_viewed(
            self.registered_user, challenge_sign_up_url
        )
        self._test_url_can_not_be_viewed(None, challenge_sign_up_url)
