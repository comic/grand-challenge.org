import re
from random import choice

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.storage import DefaultStorage
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from userena.models import UserenaSignup

from grandchallenge.challenges.models import Challenge
from grandchallenge.pages.models import Page
from grandchallenge.subdomains.utils import reverse
from tests.factories import PageFactory, RegistrationRequestFactory
from tests.utils import get_http_host

PI_LINE_END_REGEX = "(\r\n|\n)"


def create_page(
    challenge, title, content="testcontent", permission_level=None
):
    if permission_level is None:
        permission_level = Page.ALL
    return PageFactory(
        title=title,
        challenge=challenge,
        html=content,
        permission_level=permission_level,
    )


def get_first_page(challenge):
    return Page.objects.filter(challenge=challenge)[0]


def extract_form_errors(html):
    """Extract the list of errors from the form."""
    errors = re.findall(
        '<ul class="errorlist"(.*)</ul>', html.decode(), re.IGNORECASE
    )
    return errors


def find_text_between(start, end, haystack: bytes):
    """
    Return text between the first occurrence of string start and string end
    in haystack.
    """
    found = re.search(
        start + "(.*)" + end, haystack.decode(), re.IGNORECASE | re.DOTALL
    )
    if found:
        return found.group(1).strip()

    else:
        raise Exception(
            "There is no substring starting with '{}', ending"
            " with '{}' in content '{}' ".format(start, end, haystack)
        )


def extract_href_from_anchor(anchor: str):
    return find_text_between('href="', '">', anchor.encode())


def is_subset(a, b):
    """Determine if a is a subset of b."""
    all(item in a for item in b)


@override_settings(DEFAULT_FILE_STORAGE="tests.storage.MockStorage")
class GrandChallengeFrameworkTestCase(TestCase):
    def setUp(self):
        call_command("check_permissions")
        self.set_up_base()
        self.set_up_extra()

    def set_up_base(self):
        """Function will be run for all subclassed testcases."""
        self._create_root_superuser()

    def set_up_extra(self):
        """Overwrite this method in child classes."""
        pass

    def _create_root_superuser(self):
        User = get_user_model()  # noqa: N806
        try:
            self.root = User.objects.filter(username="root")[0]
        except IndexError:
            # A user who has created a project
            root = UserenaSignup.objects.create_user(
                "root", "w.s.kerkstra@gmail.com", "testpassword", active=True
            )
            root.is_staff = True
            root.is_superuser = True
            root.save()
            self.root = root

    def _create_dummy_project(self, projectname="testproject"):
        """
        Create a project with some pages and users.

        In part this is done through admin views, meaning admin views are also
        tested here.
        """
        # Create three types of users that exist: Root, can do anything,
        # projectadmin, cam do things to a project he or she owns. And logged in
        # user
        # created in  _create_main_project_and_root.
        root = self.root
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage.
        # A user who has created a project
        projectadmin = self._create_random_user("projectadmin")
        testproject = self._create_challenge_in_admin(
            projectadmin, projectname
        )
        create_page(testproject, "testpage1")
        create_page(testproject, "testpage2")
        # a user who explicitly signed up to testproject
        participant = self._create_random_user("participant")
        self._register(participant, testproject)
        # a user who only signed up but did not register to any project
        registered_user = self._create_random_user("registered")
        # TODO: How to do this gracefully?
        return [testproject, root, projectadmin, participant, registered_user]

    def _register(self, user, project):
        """
        Register user for the given project, follow actual signup as closely
        as possible.
        """
        RegistrationRequestFactory(challenge=project, user=user)
        self.assertTrue(
            project.is_participant(user),
            "After registering as user %s , user does not "
            " appear to be registered." % (user.username),
        )

    def _test_page_can_be_viewed(self, user, page):
        page_url = reverse(
            "pages:detail",
            kwargs={
                "challenge_short_name": page.challenge.short_name,
                "page_title": page.title,
            },
        )
        return self._test_url_can_be_viewed(user, page_url)

    def _test_page_can_not_be_viewed(self, user, page):
        page_url = reverse(
            "pages:detail",
            kwargs={
                "challenge_short_name": page.challenge.short_name,
                "page_title": page.title,
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

    def _find_errors_in_page(self, response):
        """
        See if there are any errors rendered in the html of response.

        Used for checking forms. Also checks for 403 response forbidden.
        Return string error message if anything does not check out, "" if not.
        """
        if response.status_code == 403:
            return "Could not check for errors, as response was a 403 response\
                     forbidden. User asking for this url did not have permission."

        errors = re.search(
            '<ul class="errorlist">(.*)</ul>',
            response.content.decode(),
            re.IGNORECASE,
        )
        if errors:
            # show a little around the actual error to scan for variables that
            # might have caused it
            span = errors.span()
            wide_start = max(span[0] - 200, 0)
            wide_end = min(span[1] + 200, len(response.content))
            wide_error = response.content[wide_start:wide_end]
            return wide_error

        else:
            # See if there are any new style errors
            soup = BeautifulSoup(response.content, "html.parser")
            errors = soup.findAll("span", attrs={"class": "invalid-feedback"})
            if len(errors) > 0:
                return str(errors)

        return ""

    def _view_url(self, user, url):
        self._login(user)

        url, kwargs = get_http_host(url=url, kwargs={})

        response = self.client.get(url, **kwargs)

        if user is None:
            username = "anonymous_user"
        else:
            username = user.username
        return response, username

    def _signup_user(self, overwrite_data=None):
        """Create a user in the same way as a new user is signed up on the project.
        any key specified in data overwrites default key passed to form.
        For example, signup_user({'username':'user1'}) to creates a user called
        'user1' and fills the rest with default data.
        """
        if overwrite_data is None:
            overwrite_data = {}
        data = {
            "first_name": "test",
            "last_name": "test",
            "username": "test",
            "email": "test@test.com",
            "password1": "testpassword",
            "password2": "testpassword",
            "institution": "test",
            "department": "test",
            "country": "NL",
            "website": "http://www.example.com",
            "accept_terms": True,
        }
        data.update(overwrite_data)  # overwrite any key in default if in data
        signin_page = self.client.post(reverse("profile_signup"), data)
        # check whether signin succeeded. If succeeded the response will be a
        # httpResponseRedirect object, which has a 'Location' key in its
        # items(). Don't know how to better check for type here.
        lst = [x[0] for x in signin_page.items()]
        self.assertTrue(
            "Location" in lst,
            "could not create user. errors in"
            " html:\n %s \n posted data: %s"
            % (extract_form_errors(signin_page.content), data),
        )

    def _create_random_user(self, startname=""):
        username = startname + "".join(
            [choice("AEOUY") + choice("QWRTPSDFGHHKLMNB") for x in range(3)]
        )
        data = {"username": username, "email": username + "@test.com"}
        return self._create_user(data)

    def _create_user(self, data):
        """
        Sign up user in a way as close to production as possible.

        Check a lot of stuff. Data is a dictionary form_field:for_value pairs.
        Any unspecified values are given default values.
        """
        username = data["username"]
        self._signup_user(data)
        validation_mail = mail.outbox[-1]
        self.assertTrue(
            "signup" in validation_mail.subject,
            "There was no email"
            " sent which had 'signup' in the subject line",
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
        response = self.client.get(validationlink)
        self.assertEqual(
            response.status_code,
            302,
            "Could not load user validation link. Expected"
            " a redirect (HTTP 302), got HTTP {} instead".format(
                response.status_code
            ),
        )
        resp = self.client.get("/accounts/" + username + "/")
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

    def _try_create_challenge(
        self, user, short_name, description="test project"
    ):
        url = reverse("challenges:create")
        storage = DefaultStorage()
        banner = storage._open("fake_test_dir/fakefile2.jpg")
        data = {
            "short_name": short_name,
            "description": description,
            "skin": "fake_test_dir/fakecss.css",
            "logo": "fakelogo.jpg",
            "banner": banner,
            "prefix": "form",
            "page_set-TOTAL_FORMS": "0",
            "page_set-INITIAL_FORMS": "0",
            "page_set-MAX_NUM_FORMS": "",
        }
        self._login(user)
        response = self.client.post(url, data)
        return response

    def _create_challenge_in_admin(
        self, user, short_name, description="test project"
    ):
        """Create a challenge object as if created through django admin interface."""
        response = self._try_create_challenge(user, short_name, description)
        errors = self._find_errors_in_page(response)
        if errors:
            self.assertFalse(
                errors, f"Error creating project '{short_name}':\n {errors}"
            )
        # ad.set_base_permissions(request,project)
        project = Challenge.objects.get(short_name=short_name)
        return project

    def _login(self, user, password="testpassword"):
        """
        Log in user an assert whether it worked.

        Passing None as user will log out.
        """
        self.client.logout()
        if user is None:
            return  # just log out

        success = self.client.login(username=user.username, password=password)
        self.assertTrue(
            success,
            "could not log in as user %s using password %s"
            % (user.username, password),
        )
        return success

    def assert_email(self, email, email_expected):
        """
        Convenient way to check subject, content, mailto etc at once for an email.

        email : django.core.mail.message object
        email_expected : dict like {"subject":"Registration complete","to":"user@email.org" }
        """
        for attr in email_expected.keys():
            try:
                found = getattr(email, attr)
            except AttributeError as e:
                raise AttributeError(
                    "Could not find attribute '{}' for this email.\
                                     are you sure it exists? - {}".format(
                        attr, str(e)
                    )
                )

            expected = email_expected[attr]
            self.assertTrue(
                expected == found
                or is_subset(found, expected)
                or (expected in found),
                "Expected to find '{}' for email attribute \
                '{}' but found '{}' instead".format(
                    expected, attr, found
                ),
            )


class CreateProjectTest(GrandChallengeFrameworkTestCase):
    def test_cannot_create_project_with_weird_name(self):
        """
        Expose issue #222 : projects can be created with names which are
        not valid as hostname, for instance containing underscores. Make sure
        These cannot be created
        """
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage.
        # A user who has created a project
        self.projectadmin = self._create_random_user("projectadmin")
        challenge_short_name = "under_score"
        response = self._try_create_challenge(
            self.projectadmin, challenge_short_name
        )
        errors = self._find_errors_in_page(response)
        self.assertTrue(
            errors,
            "Creating a project called '{}' should not be \
            possible. But is seems to have been created anyway.".format(
                challenge_short_name
            ),
        )
        challenge_short_name = "project with spaces"
        response = self._try_create_challenge(
            self.projectadmin, challenge_short_name
        )
        errors = self._find_errors_in_page(response)
        self.assertTrue(
            errors,
            "Creating a project called '{}' should not be \
            possible. But is seems to have been created anyway.".format(
                challenge_short_name
            ),
        )
        challenge_short_name = "project-with-w#$%^rd-items"
        response = self._try_create_challenge(
            self.projectadmin, challenge_short_name
        )
        errors = self._find_errors_in_page(response)
        self.assertTrue(
            errors,
            "Creating a project called '{}' should not be \
            possible. But is seems to have been created anyway.".format(
                challenge_short_name
            ),
        )
        challenge_short_name = "images"
        response = self._try_create_challenge(
            self.projectadmin, challenge_short_name
        )
        errors = self._find_errors_in_page(response)
        self.assertTrue(
            errors,
            "Creating a project called '{}' should not be \
            possible. But is seems to have been created anyway.".format(
                challenge_short_name
            ),
        )


class ViewsTest(GrandChallengeFrameworkTestCase):
    def set_up_extra(self):
        """
        Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # todo: is this ugly? At least there is explicit assignment of vars.
        # How to do this better?
        [
            self.testproject,
            self.root,
            self.projectadmin,
            self.participant,
            self.registered_user,
        ] = self._create_dummy_project("view-test")

    def test_registered_user_can_create_project(self):
        """
        A user freshly registered through the challenge can immediately create
        a challenge.
        """
        user = self._create_user({"username": "user2", "email": "ab@cd.com"})
        testproject = self._create_challenge_in_admin(user, "user1project")
        testpage1 = create_page(testproject, "testpage1")
        create_page(testproject, "testpage2")
        self._test_page_can_be_viewed(user, testpage1)
        self._test_page_can_be_viewed(self.root, testpage1)

    def test_page_view_permission(self):
        """
        Check that a page with permissions set can only be viewed by the
        correct users.
        """
        adminonlypage = create_page(
            self.testproject, "adminonlypage", permission_level=Page.ADMIN_ONLY
        )
        registeredonlypage = create_page(
            self.testproject,
            "registeredonlypage",
            permission_level=Page.REGISTERED_ONLY,
        )
        publicpage = create_page(
            self.testproject, "publicpage", permission_level=Page.ALL
        )
        self._test_page_can_be_viewed(self.projectadmin, adminonlypage)
        self._test_page_can_not_be_viewed(self.participant, adminonlypage)
        self._test_page_can_not_be_viewed(self.registered_user, adminonlypage)
        self._test_page_can_not_be_viewed(
            None, adminonlypage
        )  # None = not logged in
        self._test_page_can_be_viewed(self.projectadmin, registeredonlypage)
        self._test_page_can_be_viewed(self.participant, registeredonlypage)
        self._test_page_can_not_be_viewed(
            self.registered_user, registeredonlypage
        )
        self._test_page_can_not_be_viewed(
            None, registeredonlypage
        )  # None = not logged in
        self._test_page_can_be_viewed(self.projectadmin, publicpage)
        self._test_page_can_be_viewed(self.participant, publicpage)
        self._test_page_can_be_viewed(self.registered_user, publicpage)
        self._test_page_can_be_viewed(None, publicpage)  # None = not logged in

    def test_robots_txt_can_be_loaded(self):
        """Check there are no errors in finding robots.txt."""
        # main domain robots.txt
        robots_url = "/robots.txt/"
        robots_url_project = reverse(
            "subdomain_robots_txt",
            kwargs={"challenge_short_name": self.testproject.short_name},
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
                "challenge_short_name": self.testproject.short_name,
                "page_title": "doesnotexistpage",
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

    def test_non_exitant_project_gives_404_or_302(self):
        """Reproduces https://github.com/comic/grand-challenge.org/issues/219."""
        # main domain robots.txt
        non_existant_url = reverse(
            "pages:home",
            kwargs={"challenge_short_name": "nonexistingproject"},
        )
        response, username = self._view_url(None, non_existant_url)

        # We redirect to the main challenge if it is not found
        self.assertEqual(
            response.status_code,
            302,
            "Expected non existing url"
            "'%s' to give 302, instead found %s"
            % (non_existant_url, response.status_code),
        )


class ProjectLoginTest(GrandChallengeFrameworkTestCase):
    """
    Getting userena login and signup to display inside a project context
    (with correct banner and pages, sending project-based email etc..) was
    quite a hassle, not to mention messy. Do all the links still work?
    """

    def set_up_extra(self):
        """
        Create some objects to work with, In part this is done through admin
        views, meaning admin views are also tested here.
        """
        [
            self.testproject,
            self.root,
            self.projectadmin,
            self.participant,
            self.signedup_user,
        ] = self._create_dummy_project("test-project")
        self.participant2 = self._create_random_user("participant2")
        self._register(self.participant2, self.testproject)

    def test_project_login(self):
        # see if login for specific project works. This tests the project
        # centered signup form.
        self._create_random_user()
        # see if views work and all urls can be found
        login_url = reverse("userena_signin")
        logout_url = reverse("userena_signout")
        profile_signup_complete_url = reverse("profile_signup_complete")
        self._test_url_can_be_viewed(self.signedup_user, login_url)
        self._test_url_can_be_viewed(None, login_url)
        self._test_url_can_be_viewed(self.participant, logout_url)
        self._test_url_can_be_viewed(None, logout_url)
        self._test_url_can_be_viewed(
            self.signedup_user, profile_signup_complete_url
        )
        self._test_url_can_be_viewed(None, profile_signup_complete_url)
        # password reset is in the "forgot password?" link on the project
        # based login page. Make sure this works right.
        self._test_url_can_be_viewed(
            self.participant, reverse("userena_password_reset")
        )


# The other userena urls are not realy tied up with project so I will
# leave to userena to test.
