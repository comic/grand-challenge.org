import re
from io import StringIO
from random import choice, randint

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from userena.models import UserenaSignup

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.utils.HtmlLinkReplacer import HtmlLinkReplacer
from grandchallenge.pages.models import Page
from grandchallenge.uploads.views import upload_handler
from tests.factories import PageFactory, RegistrationRequestFactory

# Platform independent regex which will match line endings in win and linux
PI_LINE_END_REGEX = "(\r\n|\n)"


def create_page(comicsite, title, content="testcontent", permission_lvl=None):
    if permission_lvl is None:
        permission_lvl = Page.ALL
    return PageFactory(
        title=title,
        challenge=comicsite,
        html=content,
        permission_lvl=permission_lvl,
    )


def get_first_page(comicsite):
    """ Get the first page of comicsite, saves some typing..
    """
    return Page.objects.filter(challenge=comicsite)[0]


def extract_form_errors(html):
    """ If something in post to a form url fails, I want to know what the
    problem was.
    
    """
    errors = re.findall(
        '<ul class="errorlist"(.*)</ul>', html.decode(), re.IGNORECASE
    )
    return errors


def find_text_between(start, end, haystack: bytes):
    """ Return text between the first occurence of string start and 
    string end in haystack. 
     
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
    """ For a html link like '<a href="www.some.nl">click here</a>' 
    return only 'www.some.nl'
    """
    return find_text_between('href="', '">', anchor.encode())


def is_subset(listA, listB):
    """ True if listA is a subset of listB 
    """
    all(item in listA for item in listB)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
@override_settings(
    PASSWORD_HASHERS=("django.contrib.auth.hashers.SHA1PasswordHasher",)
)
@override_settings(DEFAULT_FILE_STORAGE="tests.storage.MockStorage")
@override_settings(SITE_ID=1)
class ComicframeworkTestCase(TestCase):
    """ Contains methods for creating users using comicframework interface
    """

    def setUp(self):
        call_command("check_permissions")
        self.setUp_base()
        self.setUp_extra()

    def setUp_base(self):
        """ This setup should be run for all comic framework testcases
        """
        self._create_main_project_and_root()

    def setUp_extra(self):
        """ Overwrite this method in child classes 
        """
        pass

    def _create_main_project_and_root(self):
        """ Everything in the framework assumes that there is one main project which
        is always shown in a bar at the very top of the page. Make sure this exists
         
        Do not create this project through admin because admin will throw an error
        at this point because MAIN_PROJECT can not be found. Chicken Egg. 
        
        Create root user to have an admin user for main project. Root is automatically
        admin for every project
        """
        if (
            len(
                Challenge.objects.filter(short_name=settings.MAIN_PROJECT_NAME)
            )
            == 0
        ):
            main = Challenge.objects.create(
                short_name=settings.MAIN_PROJECT_NAME,
                description="main project, autocreated by comicframeworkTestCase._create_inital_project()",
            )
            main.save()
        User = get_user_model()
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
        """ Create a project with some pages and users. In part this is 
        done through admin views, meaning admin views are also tested here.
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
        testproject = self._create_comicsite_in_admin(
            projectadmin, projectname
        )
        create_page(testproject, "testpage1")
        create_page(testproject, "testpage2")
        # a user who explicitly signed up to testproject
        participant = self._create_random_user("participant")
        self._register(participant, testproject)
        # a user who only signed up but did not register to any project
        registered_user = self._create_random_user("comicregistered")
        # TODO: How to do this gracefully?
        return [testproject, root, projectadmin, participant, registered_user]

    def _register(self, user, project):
        """ Register user for the given project, follow actual signup as
        closely as possible.
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
        """ see if there are any errors rendered in the html of reponse.
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
        response = self.client.get(url)
        if user is None:
            username = "anonymous_user"
        else:
            username = user.username
        return response, username

    def _signup_user(self, overwrite_data=None, site=None):
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

    def _create_random_user(self, startname="", site=None):
        """ Sign up a user, saves me having to think of a unique name each time
        predend startname if given
        """
        username = startname + "".join(
            [choice("AEOUY") + choice("QWRTPSDFGHHKLMNB") for x in range(3)]
        )
        data = {"username": username, "email": username + "@test.com"}
        return self._create_user(data)

    def _create_user(self, data):
        """ Sign up user in a way as close to production as possible. Check a 
        lot of stuff. Data is a dictionary form_field:for_value pairs. Any
        unspecified values are given default values
        
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
        pattern = "/example.com(.*)" + PI_LINE_END_REGEX
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
        User = get_user_model()
        query_result = User.objects.filter(username=username)
        return query_result[0]

    def _try_create_comicsite(
        self, user, short_name, description="test project"
    ):
        """ split this off from create_comicsite because sometimes you just
        want to assert that creation fails
        """
        url = reverse("challenges:create")
        factory = RequestFactory()
        storage = DefaultStorage()
        banner = storage._open(
            settings.COMIC_PUBLIC_FOLDER_NAME + "/fakefile2.jpg"
        )
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
        success = self._login(user)
        response = self.client.post(url, data)
        return response

    def _create_comicsite_in_admin(
        self, user, short_name, description="test project"
    ):
        """ Create a comicsite object as if created through django admin interface.
        
        """
        # project = ComicSite.objects.create(short_name=short_name,
        # description=description,
        # header_image=settings.COMIC_PUBLIC_FOLDER_NAME+"fakefile2.jpg")
        # project.save()
        # because we are creating a comicsite directly, some methods from admin
        # are not being called as they should. Do this manually
        # ad = ComicSiteAdmin(project,admin.site)
        response = self._try_create_comicsite(user, short_name, description)
        errors = self._find_errors_in_page(response)
        if errors:
            self.assertFalse(
                errors, f"Error creating project '{short_name}':\n {errors}"
            )
        # ad.set_base_permissions(request,project)
        project = Challenge.objects.get(short_name=short_name)
        return project

    def _login(self, user, password="testpassword"):
        """ convenience function. log in user an assert whether it worked.
        passing None as user will log out
        
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

    def assertEmail(self, email, email_expected):
        """ Convenient way to check subject, content, mailto etc at once for
        an email 
        
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

    def apply_standard_middleware(self, request):
        """ Some actions in the admin pages require certain middleware which is not
        always present in admin. Apply this explicitly here.
        
        """
        from django.contrib.sessions.middleware import (
            SessionMiddleware
        )  # Some admin actions render messages and will crash without explicit import
        from django.contrib.messages.middleware import MessageMiddleware
        from grandchallenge.core.middleware.project import ProjectMiddleware

        sm = SessionMiddleware()
        mm = MessageMiddleware()
        pm = ProjectMiddleware()
        sm.process_request(request)
        mm.process_request(request)
        pm.process_request(request)


class CreateProjectTest(ComicframeworkTestCase):
    def test_cannot_create_project_with_weird_name(self):
        """ Expose issue #222 : projects can be created with names which are
        not valid as hostname, for instance containing underscores. Make sure
        These cannot be created 
        
        """
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage.
        # A user who has created a project
        self.projectadmin = self._create_random_user("projectadmin")
        # self.testproject = self._create_comicsite_in_admin(self.projectadmin,"under_score")
        challenge_short_name = "under_score"
        response = self._try_create_comicsite(
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
        response = self._try_create_comicsite(
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
        response = self._try_create_comicsite(
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
        response = self._try_create_comicsite(
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


class ViewsTest(ComicframeworkTestCase):
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
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
        """ A user freshly registered through the project can immediately create
        a project
        
        """
        user = self._create_user({"username": "user2", "email": "ab@cd.com"})
        testproject = self._create_comicsite_in_admin(user, "user1project")
        testpage1 = create_page(testproject, "testpage1")
        testpage2 = create_page(testproject, "testpage2")
        self._test_page_can_be_viewed(user, testpage1)
        self._test_page_can_be_viewed(self.root, testpage1)

    def test_page_view_permission(self):
        """ Check that a page with permissions set can be viewed by the correct
        users only
                
        """
        adminonlypage = create_page(
            self.testproject, "adminonlypage", permission_lvl=Page.ADMIN_ONLY
        )
        registeredonlypage = create_page(
            self.testproject,
            "registeredonlypage",
            permission_lvl=Page.REGISTERED_ONLY,
        )
        publicpage = create_page(
            self.testproject, "publicpage", permission_lvl=Page.ALL
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
        """ Just check there are no errors in finding robots.txt. Only testing
        for non-logged in users because I would hope bots are never logged in 
        
        """
        # main domain robots.txt
        robots_url = "/robots.txt/"
        # robots.txt for each project, which by bots can be seen as seperate
        # domain beacuse we use dubdomains to designate projects
        robots_url_project = reverse(
            "comicsite_robots_txt",
            kwargs={"challenge_short_name": self.testproject.short_name},
        )
        self._test_url_can_be_viewed(None, robots_url)  # None = not logged in
        self._test_url_can_be_viewed(
            None, robots_url_project
        )  # None = not logged in

    def test_non_exitant_page_gives_404(self):
        """ reproduces issue #219
        https://github.com/comic/grand-challenge.org/issues/219
        
        """
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

    def test_non_exitant_project_gives_404(self):
        """ reproduces issue #219,
        https://github.com/comic/grand-challenge.org/issues/219
        
        """
        # main domain robots.txt
        non_existant_url = reverse(
            "challenge-homepage",
            kwargs={"challenge_short_name": "nonexistingproject"},
        )
        response, username = self._view_url(None, non_existant_url)
        self.assertEqual(
            response.status_code,
            404,
            "Expected non existing url"
            "'%s' to give 404, instead found %s"
            % (non_existant_url, response.status_code),
        )


class LinkReplacerTest(ComicframeworkTestCase):
    """ Tests module which makes sure relative/absolute links in included files
    will point to the right places.
      
    """

    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        [
            self.testproject,
            self.root,
            self.projectadmin,
            self.participant,
            self.signedup_user,
        ] = self._create_dummy_project("linkreplacer-test")
        self.replacer = HtmlLinkReplacer()

    def assert_substring_in_string(self, substring, string):
        self.assertTrue(
            substring in string,
            "expected substring '{}' ,was not found in {}".format(
                substring, string
            ),
        )

    def test_replace_links(self):
        from django.core.files.storage import default_storage

        # this fake file is included on test pa
        default_storage.add_fake_file(
            "fakeincludeurls.html",
            "<relativelink><a href = 'relative.html'>link</a><endrelativelink>"
            "<pathrelativeink><a href = 'folder1/relative.html'>link</a><endpathrelativelink>"
            "<moveuplink><a href = '../moveup.html'>link</a><endmoveuplink>"
            "<absolute><a href = 'http://www.hostname.com/somelink.html'>link</a><endabsolute>"
            "<absolute><a href = 'http://www.hostname.com/somelink.html'>link</a><endabsolute>"
            "<notafile><a href = '/faq'>link</a><endnotafile>"
            "<notafile_slash><a href = '/faq/'>link</a><endnotafile_slash>",
        )
        content = "Here is an included file: <toplevelcontent> {% insert_file public_html/fakeincludeurls.html %}</toplevelcontent>"
        insertfiletagpage = create_page(
            self.testproject, "testincludefiletagpage", content
        )
        response = self._test_page_can_be_viewed(
            self.signedup_user, insertfiletagpage
        )
        # Extract rendered content from included file, see if it has been rendered
        # In the correct way
        relative = find_text_between(
            "<relativelink>", "<endrelativelink>", response.content
        )
        pathrelativelink = find_text_between(
            "<pathrelativeink>", "<endpathrelativelink>", response.content
        )
        moveuplink = find_text_between(
            "<moveuplink>", "<endmoveuplink>", response.content
        )
        absolute = find_text_between(
            "<absolute>", "<endabsolute>", response.content
        )
        notafile = find_text_between(
            "<notafile>", "<endnotafile>", response.content
        )
        notafile_slash = find_text_between(
            "<notafile_slash>", "<endnotafile_slash>", response.content
        )
        relative_expected = 'href="/site/linkreplacer-test/testincludefiletagpage/insert/public_html/relative.html'
        pathrelativelink_expected = 'href="/site/linkreplacer-test/testincludefiletagpage/insert/public_html/folder1/relative.html'
        moveuplink_expected = 'href="/site/linkreplacer-test/testincludefiletagpage/insert/public_html/../moveup.html'
        absolute_expected = 'href="http://www.hostname.com/somelink.html'
        notafile_expected = 'href="/faq"'
        notafile_slash_expected = 'href="/faq/"'
        self.assert_substring_in_string(relative_expected, relative)
        self.assert_substring_in_string(
            pathrelativelink_expected, pathrelativelink
        )
        self.assert_substring_in_string(moveuplink_expected, moveuplink)
        self.assert_substring_in_string(absolute_expected, absolute)
        self.assert_substring_in_string(notafile_expected, notafile)
        self.assert_substring_in_string(
            notafile_slash_expected, notafile_slash
        )


class UploadTest(ComicframeworkTestCase):
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
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

    def test_file_upload_page_shows(self):
        """ The /files page should show to admin, signedin and root, but not
        to others
        """
        url = reverse(
            "uploads:create",
            kwargs={"challenge_short_name": self.testproject.short_name},
        )
        self._test_url_can_be_viewed(self.root, url)

    # self._test_url_can_be_viewed(self.root.username,url)
    def _upload_test_file(self, user, project, testfilename=""):
        """ Upload a very small text file as user to project, through standard
        upload view at /files 
        
        """
        if testfilename == "":
            testfilename = self.giverandomfilename(user)
        url = reverse(
            "uploads:create",
            kwargs={"challenge_short_name": self.testproject.short_name},
        )
        factory = RequestFactory()
        request = factory.get(url)
        request.user = user
        fakefile = File(StringIO("some uploaded content for" + testfilename))
        fakecontent = "some uploaded content for" + testfilename
        request.FILES["file"] = SimpleUploadedFile(
            name=testfilename, content=fakecontent.encode()
        )
        request.method = "POST"

        # Some magic code to fix a bug with middleware not being found,
        # don't know what this does but if fixes the bug.
        from django.contrib.messages.storage.fallback import FallbackStorage

        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)
        response = upload_handler(request, project.short_name)
        self.assertEqual(
            response.status_code,
            302,
            "Uploading file %s as "
            "user %s to project %s did not load to expected 302 "
            % (testfilename, user.username, project.short_name),
        )
        errors = self._find_errors_in_page(response)
        if errors:
            self.assertFalse(
                errors,
                "Error uploading file '%s':\n %s"
                % (testfilename, errors.group(1)),
            )
        return response

    def giverandomfilename(self, user, postfix=""):
        """ Create a filename where you can see from which user is came, but 
        you don't get any nameclashes when creating a few
        """
        return "{}_{}_{}".format(
            user.username,
            str(randint(10000, 99999)),
            "testfile%s.txt" % postfix,
        )

    def test_file_can_be_uploaded(self):
        """ Upload a fake file, see if correct users can see this file
        """
        project = self.testproject
        name1 = self.giverandomfilename(self.root)
        name2 = self.giverandomfilename(self.projectadmin)
        name3 = self.giverandomfilename(self.participant)
        name4 = self.giverandomfilename(self.participant2)
        resp1 = self._upload_test_file(self.root, self.testproject, name1)
        resp2 = self._upload_test_file(
            self.projectadmin, self.testproject, name2
        )
        resp3 = self._upload_test_file(
            self.participant, self.testproject, name3
        )
        resp4 = self._upload_test_file(
            self.participant2, self.testproject, name4
        )


class TemplateTagsTest(ComicframeworkTestCase):
    """ See if using template tags like {% include file.txt %} inside page html
    will crash anything
    
    """

    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
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

        from django.core.files.storage import default_storage

        # this fake file is included on test pages later to test rendering
        default_storage.add_fake_file(
            "fakeinclude.html",
            "This is some fake include content:"
            "here is the content of fakecss"
            "<somecss>{% insert_file "
            + default_storage.FAKE_DIRS[1]
            + "/fakecss.css %} </somecss>and a "
            "non-existant include: <nonexistant>{% insert_file nothing/nonexistant.txt %}</nonexistant> Also"
            " try to include scary file path <scary>{% insert_file ../../../allyoursecrets.log %}</scary>",
        )

    def _extract_download_link(self, response1):
        """ From a page rendering a listfile template tag, return the first
        download link
        
        """
        found = re.search(
            '<ul class="dataset">(.*)</ul>',
            response1.content.decode(),
            re.IGNORECASE,
        )
        link = ""
        if found:
            filelist_HTML = found.group(0).strip()
            found_link = re.search(
                'href="(.*)">', found.group(0), re.IGNORECASE
            )
            if found_link:
                link = found_link.group(1).strip()
        self.assertTrue(
            link != "",
            "Could not find any list of files after rendering html '%s'"
            % response1.content,
        )
        return link

    def test_listdir(self):
        """ Does the template tag for listing and downloading files in a dir work
        correctly? 
        
        test for comcisite.templatetags.templatetags.listdir
        
        """
        # create a page containing the listdir tag on the public folder.
        # Path to browse is a special path for which Mockstorage will return some
        # file list even if it does not exist
        content = (
            "Here are all the files in dir: {% listdir path:"
            + settings.COMIC_PUBLIC_FOLDER_NAME
            + " extensionFilter:.mhd %} text after "
        )
        page1 = create_page(self.testproject, "listdirpage", content)
        # can everyone now view this?
        response1 = self._test_page_can_be_viewed(None, page1)
        response1 = self._test_page_can_be_viewed(self.root, page1)
        response2 = self._test_page_can_be_viewed(self.signedup_user, page1)
        # open one of the download links from the file list
        # see if there are any errors rendered in the reponse
        link = self._extract_download_link(response1)
        self._test_url_can_be_viewed(self.root, link)
        self._test_url_can_be_viewed(self.signedup_user, link)
        # Now check files listed in a restricted area. These should only be
        # accessible tp registered users
        content = (
            "Here are all the files in dir: {% listdir path:"
            + settings.COMIC_REGISTERED_ONLY_FOLDER_NAME
            + " extensionFilter:.mhd %} text after "
        )
        page2 = create_page(self.testproject, "restrictedlistdirpage", content)
        # can everyone now view this page?
        response5 = self._test_page_can_be_viewed(self.root, page2)
        response6 = self._test_page_can_be_viewed(self.signedup_user, page2)
        # A download link from a restricted path should only be loadable by
        # participants that registered with the challenge
        link = self._extract_download_link(response5)
        self._test_url_can_be_viewed(self.root, link)
        self._test_url_can_be_viewed(self.participant, link)
        self._test_url_can_not_be_viewed(self.signedup_user, link)
        self._test_url_can_not_be_viewed(None, link)  # not logged in user
        # are there gracefull errors for non existsing dirs?
        content = "Here are all the files in a non existing dir: {% listdir path:not_existing/ extensionFilter:.mhd %} text after "
        page2 = create_page(
            self.testproject, "list_non_exisiting_dir_page", content
        )
        self._test_page_can_be_viewed(self.root, page2)
        self._test_page_can_be_viewed(self.signedup_user, page2)

    def test_url_tag(self):
        """ url tag returns a url to view a given objects. Comicframework uses
        a custom url tag to be able use subdomain rewriting. 
        
        """
        # Sanity check: do two different pages give different urls?
        content = (
            "-url1-{% url 'pages:detail' '"
            + self.testproject.short_name
            + "' 'testurlfakepage1' %}-endurl1-"
        )
        content += (
            "-url2-{% url 'pages:detail' '"
            + self.testproject.short_name
            + "' 'testurlfakepage2' %}-endurl2-"
        )
        urlpage = create_page(self.testproject, "testurltagpage", content)
        # SUBDOMAIN_IS_PROJECTNAME affects the way urls are rendered
        with self.settings(SUBDOMAIN_IS_PROJECTNAME=False):
            response = self._test_page_can_be_viewed(
                self.signedup_user, urlpage
            )
            url1 = find_text_between("-url1-", "-endurl1", response.content)
            url2 = find_text_between("-url2-", "-endurl2", response.content)
            self.assertTrue(
                url1 != url2,
                "With SUBDOMAIN_IS_PROJECTNAME = False"
                " URL tag gave the same url for two different "
                "pages. Both 'testurlfakepage1' and "
                "'testurlfakepage1' got url '%s'" % url1,
            )
        with self.settings(SUBDOMAIN_IS_PROJECTNAME=True):
            response = self._test_page_can_be_viewed(
                self.signedup_user, urlpage
            )
            url1 = find_text_between("-url1-", "-endurl1", response.content)
            url2 = find_text_between("-url2-", "-endurl2", response.content)
            self.assertTrue(
                url1 != url2,
                "With SUBDOMAIN_IS_PROJECTNAME = True"
                " URL tag gave the same url for two different "
                "pages. Both 'testurlfakepage1' and "
                "'testurlfakepage1' got url '%s'" % url1,
            )

    def test_insert_file_tag(self):
        """ Can directly include the contents of a file. Contents can again 
        include files.  
        
        """
        content = "Here is an included file: <toplevelcontent> {% insert_file public_html/fakeinclude.html %}</toplevelcontent>"
        insertfiletagpage = create_page(
            self.testproject, "testincludefiletagpage", content
        )
        response = self._test_page_can_be_viewed(
            self.signedup_user, insertfiletagpage
        )
        # Extract rendered content from included file, see if it has been rendered
        # In the correct way
        somecss = find_text_between(
            "<somecss>", "</somecss>", response.content
        )
        nonexistant = find_text_between(
            "<nonexistant>", "</nonexistant>", response.content
        )
        scary = find_text_between("<scary>", "</scary>", response.content)
        self.assertTrue(
            somecss != "",
            "Nothing was rendered when including an existing file. Some css should be here",
        )
        self.assertTrue(
            nonexistant != "",
            "Nothing was rendered when including an existing file. Some css should be here",
        )
        self.assertTrue(
            scary != "",
            "Nothing was rendered when trying to go up the directory tree with ../ At least some error should be printed",
        )
        self.assertTrue(
            "body {width:300px;}" in somecss,
            "Did not find expected"
            " content 'body {width:300px;}' when including a test"
            " css file. Instead found '%s'" % somecss,
        )
        self.assertTrue(
            "Error including file" in nonexistant,
            "Expected a"
            " message 'Error including file' when including "
            "non-existant file. Instead found '%s'" % nonexistant,
        )
        self.assertTrue(
            "Error including file" in scary,
            "Expected a message 'Error including file' when trying to include filepath with ../"
            " in it. Instead found '%s'" % scary,
        )

    def get_mail_html_part(self, mail):
        """ Extract html content from email sent with models.challenge.send_templated_email
        
        """
        return mail.alternatives[0][0]

    def assertText(self, content, expected_text, description=""):
        """ assert that expected_text can be found in text, 
        description can describe what this link should do, like
        "register user without permission", for better fail messages
                
        """
        self.assertTrue(
            expected_text in content.decode(),
            "expected to find '{}' but found '{}' instead.\
                         Attemted action: {}".format(
                expected_text, content, description
            ),
        )

    def assertTextBetweenTags(
        self, text, tagname, expected_text, description=""
    ):
        """ Assert whether expected_text was found in between <tagname> and </tagname>
        in text. On error, will include description of operation, like "trying to render
        table from csv".
        
        """
        content = find_text_between(
            "<" + tagname + ">", "</" + tagname + ">", text
        )
        self.assertTrue(
            content != "",
            "Nothing was rendered between <{0}> </{0}>, attempted action: {1}".format(
                tagname, description
            ),
        )
        description = (
            "Rendering tag between <{0}> </{0}>, ".format(tagname)
            + description
        )
        self.assertText(text, expected_text, description)


class ProjectLoginTest(ComicframeworkTestCase):
    """ Getting userena login and signup to display inside a project context 
    (with correct banner and pages, sending project-based email etc..) was quite
    a hassle, not to mention messy. Do all the links still work?
    
    """

    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
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
        self._create_random_user(site=self.testproject)
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
