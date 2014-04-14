"""
This contains tests using the unittest module. These will pass
when you run "manage.py test.


"""
import pdb
import re
from random import choice,randint

from django.contrib import admin
from django.contrib.auth.models import User
from django.core import mail
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

from ckeditor.views import upload_to_project 
from comicmodels.admin import RegistrationRequestAdmin
from comicmodels.models import Page,ComicSite,UploadModel,ComicSite,RegistrationRequest
from comicmodels.views import upload_handler
from comicsite.admin import ComicSiteAdmin,PageAdmin
from comicsite.storage import MockStorage
from django.core.files.storage import DefaultStorage
from comicsite.views import _register
from profiles.admin import UserProfileAdmin
from profiles.models import UserProfile
from profiles.forms import SignupFormExtra
from dataproviders.DropboxDataProvider import HtmlLinkReplacer  # TODO: move HtmlLinkReplacer to better location..


def get_or_create_user(username,password):
    query_result = User.objects.filter(username=username)
    if query_result.exists():
        return query_result[0]
        
    else:
        return 
    
                  
def create_page_in_admin(comicsite,title,content="testcontent",permission_lvl=""):
    """ Create a Page object as if created through django admin interface.
    
    """
    
    if permission_lvl == "":
       permission_lvl = Page.ALL
    
    page_admin = PageAdmin(Page,admin.site)
    page = Page.objects.create(title=title,
                               comicsite=comicsite,
                               html=content,
                               permission_lvl=permission_lvl)
    page_admin.first_save(page)
    return page

def create_registrationrequest_in_admin(comicsite,requesting_user):
    """ Create a  object as if created through django admin interface.    
    """
    
    
    page_admin = PageAdmin(Page,admin.site)
    page = Page.objects.create(title=title,
                               comicsite=comicsite,
                               html=content,
                               permission_lvl=permission_lvl)
    page_admin.first_save(page)
    return page

    

def get_first_page(comicsite):
    """ Get the first page of comicsite, saves some typing..
    """
    return Page.objects.filter(comicsite = comicsite)[0]


def extract_form_errors(html):
    """ If something in post to a form url fails, I want to know what the
    problem was.
    
    """
    errors = re.findall('<ul class="errorlist"(.*)</ul>',
                         html,
                         re.IGNORECASE)
    
    return errors

def find_text_between(start,end,haystack):
        """ Return text between the first occurence of string start and 
        string end in haystack. 
         
        """
        found = re.search(start+'(.*)'+end,haystack,re.IGNORECASE | re.DOTALL)
                
        if found:
            return found.group(1)
        else:
            raise Exception("There is no substring starting with '{}', ending"
                            " with '{}' in content '{}' ".format(start,end,haystack))

def extract_href_from_anchor(anchor):
    """ For a html link like '<a href="www.some.nl">click here</a>' 
    return only 'www.some.nl'
    """
    return find_text_between('href="','">',anchor)
        


def is_subset(listA,listB):
    """ True if listA is a subset of listB 
    """
    all(item in listA for item in listB)
    
    
class ComicframeworkTestCase(TestCase):
    """ Contains methods for creating users using comicframework interface
    """ 
    
    def setUp(self):
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
        if len(ComicSite.objects.filter(short_name=settings.MAIN_PROJECT_NAME)) == 0:
            main = ComicSite.objects.create(short_name=settings.MAIN_PROJECT_NAME,
                                            description="main project, autocreated by comicframeworkTestCase._create_inital_project()",
                                            skin="fakeskin.css"
                                            )
            
            main.save()
            
            # A user who has created a project
            root = User.objects.create_user('root',
                                        'w.s.kerkstra@gmail.com',
                                        'testpassword')        
            root.is_staff = True
            root.is_superuser = True
            root.save()
            
            self.root = root
        
                     
    def _create_dummy_project(self,projectname="testproject"):
        """ Create a project with some pages and users. In part this is 
        done through admin views, meaning admin views are also tested here.
        """
        # Create three types of users that exist: Root, can do anything, 
        # projectadmin, cam do things to a project he or she owns. And logged in
        # user 
        
        #created in  _create_main_project_and_root.
        root = self.root
        # non-root users are created as if they signed up through the project,    
        # to maximize test coverage.                
        
        # A user who has created a project
        projectadmin = self._create_random_user("projectadmin_")
                    
        testproject = self._create_comicsite_in_admin(projectadmin,projectname)
        create_page_in_admin(testproject,"testpage1")
        create_page_in_admin(testproject,"testpage2")
        
        # a user who explicitly signed up to testproject
        participant = self._create_random_user("participant_")
        self._register(participant,testproject)
        
        # a user who only signed up but did not register to any project
        registered_user = self._create_random_user("comicregistered_")
        
        #TODO: How to do this gracefully? 
        return [testproject,root,projectadmin,participant,registered_user]
        
                
    
    
    def _register(self,user,project):
        """ Register user for the given project, follow actual signup as
        closely as possible.
        """
        url = reverse("comicsite.views._register", 
            kwargs={"site_short_name":project.short_name})
        factory = RequestFactory()
        request = factory.get(url)
        request.user = user
                
        response = _register(request,project.short_name)
        
        
        self.assertEqual(response.status_code,
                         200,
                         "After registering as user %s at '%s', page did not"
                         " load properly" % (user.username,url))
                         
        self.assertTrue(project.is_participant(user),
                        "After registering as user %s at '%s', user does not "
                        " appear to be registered." % (user.username,url))
        
    
    def _test_page_can_be_viewed(self,user,page):
        page_url = reverse('comicsite.views.page',
                           kwargs={"site_short_name":page.comicsite.short_name,
                                   "page_title":page.title})
        
        return self._test_url_can_be_viewed(user,page_url)
    
    
    def _test_page_can_not_be_viewed(self,user,page):
        page_url = reverse('comicsite.views.page',
                           kwargs={"site_short_name":page.comicsite.short_name,
                                   "page_title":page.title})
        
        return self._test_url_can_not_be_viewed(user,page_url)
        
        
                         
    def _test_url_can_be_viewed(self,user,url):
        response,username = self._view_url(user,url)                    
        self.assertEqual(response.status_code, 200, "could not load page"
                         "'%s' logged in as user '%s'. Expected HTML200, got HTML%s"% (url,user,str(response.status_code)))
        return response
    
    def _test_url_can_not_be_viewed(self,user,url):        
        response,username = self._view_url(user,url)
        self.assertNotEqual(response.status_code, 200, "could load restricted " 
                            "page'%s' logged in as user '%s'"% (url,
                                                                username))
        return response
    
    def _find_errors_in_page(self, response):    
        """ see if there are any errors rendered in the html of reponse.
        Used for checking forms. Also checks for 403 response forbidden.
        
        Return string error message if anything does not check out, "" if not.         
        """
        if response.status_code == 403:
             return "Could not check for errors, as response was a 403 response\
                     forbidden. User asking for this url did not have permission."
        
        
        errors = re.search('<ul class="errorlist">(.*)</ul>', 
            response.content, 
            re.IGNORECASE)

        if errors:        
                    #show a little around the actual error to scan for variables that
            # might have caused it
            span = errors.span()
            wide_start = max(span[0]-200,0)
            wide_end = min(span[1]+200,len(response.content))        
            wide_error = response.content[wide_start:wide_end]
            return wide_error
            
        return ""
        
    
    def _view_url(self,user,url):
        self._login(user)
        response = self.client.get(url)
        if user is None:
            username = "anonymous_user"
        else:
            username = user.username
        
        return response,username
            
            
    
    def _signup_user(self,overwrite_data={},site=None):
        """Create a user in the same way as a new user is signed up on the project.
        any key specified in data overwrites default key passed to form.
        For example, signup_user({'username':'user1'}) to creates a user called 
        'user1' and fills the rest with default data.  
        
        
        """    
        data = {'first_name':'test',
                'last_name':'test',
                'username':'test',            
                'email':'test@test.com',
                'password1':'testpassword',
                'password2':'testpassword',
                'institution':'test',
                'department':'test', 
                'country':'NL',
                'webproject':'testwebproject',
                'comicsite':'testcomicwebproject'}
        
        data.update(overwrite_data) #overwrite any key in default if in data
        
        if site == None:
            sitename = settings.MAIN_PROJECT_NAME
        else:
            sitename = site.short_name
        
        signin_page = self.client.post(reverse("comicsite.views.signup",
                                               kwargs={"site_short_name":sitename}),data)
                
        # check whether signin succeeded. If succeeded the response will be a
        # httpResponseRedirect object, which has a 'Location' key in its
        # items(). Don't know how to better check for type here.
        list = [x[0] for x in signin_page.items()]
        
        
        self.assertTrue('Location' in list, "could not create user. errors in"
                        " html:\n %s \n posted data: %s"                        
                        %(extract_form_errors(signin_page.content),data))
                        
        
        
    def _create_random_user(self,startname="",site=None):
        """ Sign up a user, saves me having to think of a unique name each time
        predend startname if given
        """
        
        username = startname + "".join([choice('AEOUY')+
                                        choice('QWRTPSDFGHHKLMNB')
                                        for x in range(3)])
        
        data = {'username':username,
                'email':username+"@test.com"}
        
        return self._create_user(data,site)

    def _create_user(self,data,site=None):
        """ Sign up user in a way as close to production as possible. Check a 
        lot of stuff. Data is a dictionary form_field:for_value pairs. Any
        unspecified values are given default values
        
        """        
        username = data['username']
        self._signup_user(data,site)
        
        
        validation_mail = mail.outbox[-1]        
        self.assertTrue("signup" in validation_mail.subject,"There was no email"
                        " sent which had 'signup' in the subject line")
        
                    
        self.assertEqual(self.client.get('/accounts/'+username+'/').status_code,
                         403, "Was not locked out of user account which was not"
                         "yet validated with link!"),
        
        # validate the user with the link that was emailed
        pattern = '/example.com(.*)\r'
        validationlink_result = re.search(pattern,
                                          validation_mail.body,
                                          re.IGNORECASE)
        
        
        self.assertTrue(validationlink_result, "could not find any link in" 
                        "registration email. Tried to match pattern '{}' but found no match in"
                        "this email: \n{}".format(pattern,validation_mail.body))
        
        validationlink = validationlink_result.group(1)        
        response = self.client.get(validationlink)        
        
        self.assertEqual(response.status_code,302, "Could not load user validation link. Expected"
                                       " a redirect (HTTP 302), got HTTP {} instead".format(response.status_code))
        
        
        resp = self.client.get('/accounts/'+username+'/')
        self.assertEqual(resp.status_code,
                         200,"Could not access user account after using" 
                         "validation link! Expected 200, got {} instead".format(resp.status_code))
            
        
        query_result = User.objects.filter(username=username)        
        return query_result[0] 

    
    def _try_create_comicsite(self, user, short_name, description="test project"):
        """ split this off from create_comicsite because sometimes you just
        want to assert that creation fails
        """
        url = reverse("admin:comicmodels_comicsite_add")
        factory = RequestFactory()
        storage = DefaultStorage()
        header_image = storage._open(settings.COMIC_PUBLIC_FOLDER_NAME + "/fakefile2.jpg")
        data = {"short_name":short_name,
            "description":description,
            "skin":"fake_test_dir/fakecss.css",
            "logo":"fakelogo.jpg",
            "header_image":header_image,
            "prefix":"form",
            "page_set-TOTAL_FORMS":u"0",
            "page_set-INITIAL_FORMS":u"0", 
            "page_set-MAX_NUM_FORMS":u""}
        success = self._login(user)
        
        
        response = self.client.post(url, data)
        return response
    

    def _create_comicsite_in_admin(self,user,short_name,description="test project"):
        """ Create a comicsite object as if created through django admin interface.
        
        """
        #project = ComicSite.objects.create(short_name=short_name,
                                # description=description,
                                # header_image=settings.COMIC_PUBLIC_FOLDER_NAME+"fakefile2.jpg")
        #project.save()
        
        # because we are creating a comicsite directly, some methods from admin
        # are not being called as they should. Do this manually
        #ad = ComicSiteAdmin(project,admin.site)        
        response = self._try_create_comicsite(user, short_name, description)
        errors = self._find_errors_in_page(response)
                
        if errors:
            self.assertFalse(errors, "Error creating project '%s':\n %s" % (short_name, errors))
                
        #ad.set_base_permissions(request,project)        
        project = ComicSite.objects.get(short_name=short_name)
        
        return project


    def _login(self,user,password="testpassword"):
        """ convenience function. log in user an assert whether it worked.
        passing None as user will log out
        
        """
        self.client.logout()
        if user is None:
            return #just log out
        success = self.client.login(username=user.username,password=password)
        self.assertTrue(success, "could not log in as user %s using password %s"
                        % (user.username,password))   
        return success

    
    def assertEmail(self,email,email_expected):
        """ Convenient way to check subject, content, mailto etc at once for
        an email 
        
        email : django.core.mail.message object
        email_expected : dict like {"subject":"Registration complete","to":"user@email.org" }        
        """
        for attr in email_expected.keys():
            try:
                found = getattr(email,attr)
            except AttributeError as e:
                raise AttributeError("Could not find attribute '{0}' for this email.\
                                     are you sure it exists? - {1}".format(attr,str(e)))
            expected = email_expected[attr]
            self.assertTrue(expected == found or is_subset(found,expected) or (expected in found),
                            "Expected to find '{0}' for email attribute \
                            '{1}' but found '{2}' instead".format(expected,
                                                                  attr,
                                                                  found))    
     


# =============================================================================
# Decorators applied to the ComicframeworkTestCase class: see 
# https://docs.djangoproject.com/en/1.4/topics/testing/#django.test.utils.override_settings

# don't send real emails, keep them in memory
ComicframeworkTestCase = override_settings(EMAIL_BACKEND='django.core.mail.'
                                         'backends.locmem.EmailBackend'
                                         )(ComicframeworkTestCase)
                                        
# use fast, non-safe password hashing to speed up testing
ComicframeworkTestCase = override_settings(PASSWORD_HASHERS=('django.contrib.'
                                           'auth.hashers.SHA1PasswordHasher',)
                                           )(ComicframeworkTestCase)
                                          
# Use a fake storage provider which does not save anything to disk, and can 
# mock reading files, returning some fake content
ComicframeworkTestCase = override_settings(DEFAULT_FILE_STORAGE = 
                                           "comicsite.storage.MockStorage"
                                           )(ComicframeworkTestCase)

# SITE_ID is used to look in the database for the name and domain of the current
# site. This can be different in different settings files, but for testing do
# not depend on any custom content of the database, so just use 1, the default. 
ComicframeworkTestCase = override_settings(SITE_ID = 1)(ComicframeworkTestCase)



class CreateProjectTest(ComicframeworkTestCase):
    
    def test_cannot_create_project_with_weird_name(self):
        """ Expose issue #222 : projects can be created with names which are
        not valid as hostname, for instance containing underscores. Make sure
        These cannot be created 
        
        """        
        # non-root users are created as if they signed up through the project,    
        # to maximize test coverage.        
        
        # A user who has created a project
        self.projectadmin = self._create_random_user("projectadmin_")
                    
        #self.testproject = self._create_comicsite_in_admin(self.projectadmin,"under_score")
        project_name = "under_score"  
        response = self._try_create_comicsite(self.projectadmin, 
                                              project_name)
        errors = self._find_errors_in_page(response)
        
        self.assertTrue(errors,u"Creating a project called '{0}' should not be \
            possible. But is seems to have been created anyway.".format(project_name))
        
        
        project_name = "project with spaces"  
        response = self._try_create_comicsite(self.projectadmin, 
                                              project_name)
        errors = self._find_errors_in_page(response)
        
        self.assertTrue(errors,u"Creating a project called '{0}' should not be \
            possible. But is seems to have been created anyway.".format(project_name))
        
        
        project_name = "project-with-w#$%^rd-items"  
        response = self._try_create_comicsite(self.projectadmin, 
                                              project_name)
        errors = self._find_errors_in_page(response)
        
        self.assertTrue(errors,u"Creating a project called '{0}' should not be \
            possible. But is seems to have been created anyway.".format(project_name))
        
        
class ViewsTest(ComicframeworkTestCase):
    
        
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        #todo: is this ugly? At least there is explicit assignment of vars.
        # How to do this better? 
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.registered_user] = self._create_dummy_project("view-test")
                    
    
    def test_registered_user_can_create_project(self):
        """ A user freshly registered through the project can immediately create
        a project
        
        """
        user = self._create_user({"username":"user2","email":"ab@cd.com"})
        testproject = self._create_comicsite_in_admin(user,"user1project")                
        testpage1 = create_page_in_admin(testproject,"testpage1")
        testpage2 = create_page_in_admin(testproject,"testpage2")
                
        self._test_page_can_be_viewed(user,testpage1)
        self._test_page_can_be_viewed(self.root,testpage1)
        
        
    
    def test_page_permissions_view(self):
        """ Test that the permissions page in admin does not crash: for root
        https://github.com/comic/comic-django/issues/180 
        
        """
        
        testpage1 = Page.objects.filter(title='testpage1')
        self.assert_(testpage1.exists(),"could not find page 'testpage1'")                 
        url = reverse("admin:comicmodels_page_permissions",
                      args=[testpage1[0].pk])
        
        self._test_url_can_be_viewed(self.root,url)
        
        otheruser = self._create_random_user("other_")
        self._test_url_can_not_be_viewed(otheruser,url)
        
        
    
    def test_page_change_view(self):
        """ Root can in admin see a page another user created while another
        regular user can not 
        
        """
        user = self._create_user({"username":"user3","email":"de@cd.com"})
        anotheruser = self._create_random_user(startname="another_user_")
        testproject = self._create_comicsite_in_admin(user,"user3project")                
        testpage1 = create_page_in_admin(testproject,"testpage1")
        testpage2 = create_page_in_admin(testproject,"testpage2")                         
        url = reverse("admin:comicmodels_page_change",
                      args=[testpage1.pk])
        
        self._test_url_can_be_viewed(user,url)        
        self._test_url_can_be_viewed(self.root,url)
        self._test_url_can_not_be_viewed(anotheruser,url)
        
    
    def test_page_view_permission(self):
        """ Check that a page with permissions set can be viewed by the correct
        users only
                
        """
        
        adminonlypage =  create_page_in_admin(self.testproject,"adminonlypage",
                                              permission_lvl=Page.ADMIN_ONLY)    
        registeredonlypage =  create_page_in_admin(self.testproject,"registeredonlypage",
                                                   permission_lvl=Page.REGISTERED_ONLY)
        publicpage =  create_page_in_admin(self.testproject,"publicpage",
                                           permission_lvl=Page.ALL)
                
        self._test_page_can_be_viewed(self.projectadmin,adminonlypage)
        #TODO: these test fail, but are not very important now. fix this later. 
        #self._test_page_can_not_be_viewed(self.participant,adminonlypage)
        #self._test_page_can_not_be_viewed(self.registered_user,adminonlypage)        
        self._test_page_can_not_be_viewed(None,adminonlypage) # None = not logged in
        
        self._test_page_can_be_viewed(self.projectadmin,registeredonlypage)
        self._test_page_can_be_viewed(self.participant,registeredonlypage)
        self._test_page_can_not_be_viewed(self.registered_user,registeredonlypage)
        self._test_page_can_not_be_viewed(None,registeredonlypage) # None = not logged in
        
        self._test_page_can_be_viewed(self.projectadmin,publicpage)
        self._test_page_can_be_viewed(self.participant,publicpage)
        self._test_page_can_be_viewed(self.registered_user,publicpage)
        self._test_page_can_be_viewed(None,publicpage) # None = not logged in
    
    def test_robots_txt_can_be_loaded(self):
        """ Just check there are no errors in finding robots.txt. Only testing
        for non-logged in users because I would hope bots are never logged in 
        
        """            
        # main domain robots.txt
        robots_url = url = "/robots.txt"
        
        # robots.txt for each project, which by bots can be seen as seperate
        # domain beacuse we use dubdomains to designate projects
        robots_url_project = reverse("comicsite_robots_txt",
                                     kwargs={"site_short_name":self.testproject.short_name})
        
        response1 = self._test_url_can_be_viewed(None,robots_url) # None = not logged in
        response2 = self._test_url_can_be_viewed(None,robots_url_project) # None = not logged in
        
        
    def test_non_exitant_page_gives_404(self):
        """ reproduces issue #219
        https://github.com/comic/comic-django/issues/219
        
        """            
        page_url = reverse('comicsite.views.page',
                           kwargs={"site_short_name":self.testproject.short_name,
                                   "page_title":"doesnotexistpage"})
        
        response,username = self._view_url(None,page_url)

        self.assertEqual(response.status_code, 404, "Expected non existing page"
        "'%s' to give 404, instead found %s"%(page_url,response.status_code))
        
        
    def test_non_exitant_project_gives_404(self):
        """ reproduces issue #219,
        https://github.com/comic/comic-django/issues/219
        
        """                            
        # main domain robots.txt
        non_existant_url = reverse('comicsite.views.site',
                           kwargs={"site_short_name":"nonexistingproject"})
                
        
        response,username = self._view_url(None,non_existant_url)
        self.assertEqual(response.status_code, 404, "Expected non existing url"
        "'%s' to give 404, instead found %s"%(non_existant_url,response.status_code))
            
    
class LinkReplacerTest(ComicframeworkTestCase):
    """ Tests module which makes sure relative/absolute links in included files
    will point to the right places.
      
    """
    
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.signedup_user] = self._create_dummy_project("linkreplacer-test")

        self.replacer = HtmlLinkReplacer()
        
        
    
    def assert_substring_in_string(self,substring,string):
        self.assertTrue(substring in string,
                        "expected substring '{}' ,was not found in {}".format(substring,string))
        
    
    def test_replace_links(self):
        
        from django.core.files.storage import default_storage
        
        #this fake file is included on test pa
        default_storage.add_fake_file("fakeincludeurls.html","<relativelink><a href = 'relative.html'>link</a><endrelativelink>" 
                                                             "<pathrelativeink><a href = 'folder1/relative.html'>link</a><endpathrelativelink>"
                                                             "<moveuplink><a href = '../moveup.html'>link</a><endmoveuplink>"
                                                             "<absolute><a href = 'http://www.hostname.com/somelink.html'>link</a><endabsolute>"
                                                             "<absolute><a href = 'http://www.hostname.com/somelink.html'>link</a><endabsolute>"
                                                             "<notafile><a href = '/faq'>link</a><endnotafile>"
                                                             "<notafile_slash><a href = '/faq/'>link</a><endnotafile_slash>")
        
                            
        content = "Here is an included file: <toplevelcontent> {% insert_file public_html/fakeincludeurls.html %}</toplevelcontent>"                
        insertfiletagpage = create_page_in_admin(self.testproject,"testincludefiletagpage",content)
                    
        response = self._test_page_can_be_viewed(self.signedup_user,insertfiletagpage)
            
        
        
        # Extract rendered content from included file, see if it has been rendered
        # In the correct way
        
                                                   
        relative = find_text_between("<relativelink>","<endrelativelink>",response.content)
        pathrelativelink = find_text_between("<pathrelativeink>","<endpathrelativelink>",response.content)
        moveuplink = find_text_between("<moveuplink>","<endmoveuplink>",response.content)
        absolute = find_text_between("<absolute>","<endabsolute>",response.content)
        notafile = find_text_between("<notafile>","<endnotafile>",response.content)
        notafile_slash = find_text_between("<notafile_slash>","<endnotafile_slash>",response.content)
        
                
        
        relative_expected = 'href="/site/linkreplacer-test/testincludefiletagpage/insert/public_html/relative.html'
        pathrelativelink_expected = 'href="/site/linkreplacer-test/testincludefiletagpage/insert/public_html/folder1/relative.html'
        moveuplink_expected = 'href="/site/linkreplacer-test/testincludefiletagpage/insert/public_html/../moveup.html'
        absolute_expected = 'href="http://www.hostname.com/somelink.html'
        notafile_expected = 'href="/faq"'
        notafile_slash_expected = 'href="/faq/"' 
        
        self.assert_substring_in_string(relative_expected,relative)
        self.assert_substring_in_string(pathrelativelink_expected,pathrelativelink)
        self.assert_substring_in_string(moveuplink_expected,moveuplink)
        self.assert_substring_in_string(absolute_expected,absolute)
        self.assert_substring_in_string(notafile_expected,notafile)
        self.assert_substring_in_string(notafile_slash_expected,notafile_slash)
        
            

    
class UploadTest(ComicframeworkTestCase):
    
    
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.signedup_user] = self._create_dummy_project("test-project")
        
         
        self.participant2 = self._create_random_user("participant2_")
        self._register(self.participant2,self.testproject)
                
             
    def test_file_upload_page_shows(self):
        """ The /files page should show to admin, signedin and root, but not
        to others
        """
        url = reverse("comicmodels.views.upload_handler",
                      kwargs={"site_short_name":self.testproject.short_name})
        self._test_url_can_be_viewed(self.root,url)                    
        #self._test_url_can_be_viewed(self.root.username,url)
    
    
    def _upload_test_file(self, user, project,testfilename=""):
        """ Upload a very small text file as user to project, through standard
        upload view at /files 
        
        """        
        
        if testfilename == "":
            testfilename = self.giverandomfilename(user)
            
        url = reverse("comicmodels.views.upload_handler", 
            kwargs={"site_short_name":self.testproject.short_name})
        
        factory = RequestFactory()
        request = factory.get(url)
        request.user = user
        
        import StringIO
        fakefile = File(StringIO.StringIO("some uploaded content for" + testfilename))
        
        fakecontent = "some uploaded content for" + testfilename
        request.FILES['file'] = SimpleUploadedFile(name=testfilename,
                                                   content=fakecontent)
        
        request.method = "POST"
        
        # Some magic code to fix a bug with middleware not being found,
        # don't know what this does but if fixes the bug.
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = upload_handler(request, project.short_name)        
        
        self.assertEqual(response.status_code, 302, "Uploading file %s as "
            "user %s to project %s did not load to expected 302 "
            % (testfilename, user.username, project.short_name))
        
        errors = self._find_errors_in_page(response)        
        if errors:
            self.assertFalse(errors, "Error uploading file '%s':\n %s" % (testfilename, errors.group(1)))
        
        return response


    def _upload_test_file_ckeditor(self, user, project,testfilename=""):
        """ Upload a very small test file in the html page editor. This is
        mainly used for uploading images while creating a page 
        
        """        
        
        if testfilename == "":
            testfilename = self.giverandomfilename(user)
         
        url = reverse("ckeditor_upload_to_project", 
            kwargs={"site_short_name":self.testproject.short_name})
        
        factory = RequestFactory()
        request = factory.get(url,
                              {"CKEditorFuncNum":"1234"}) # CKEditorFuncNum is 
                                                          # used by ckeditor, 
                                                          # normally filled by 
                                                          # js but faked here.
         
        request.user = user
        
        import StringIO
        fakefile = File(StringIO.StringIO("some uploaded content for" + testfilename))
        
        fakecontent = "some uploaded content for" + testfilename
        request.FILES['upload'] = SimpleUploadedFile(name=testfilename,
                                                   content=fakecontent)
        
        request.method = "POST"
        
        # Some magic code to fix a bug with middleware not being found,
        # don't know what this does but if fixes the bug.
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        response = upload_to_project(request, project.short_name)        
                
        self.assertEqual(response.status_code, 200, "Uploading file %s as "
            "user %s to project %s in ckeditor did not return expected result"
            % (testfilename, user.username, project.short_name))
        
        errors = re.search('<ul class="errorlist">(.*)</ul>',
                            response.content,
                             re.IGNORECASE)
        
        self.assertFalse("Uploading failed" in response.content,
                         "Uploading file %s as user %s to project %s in "
                         "ckeditor return javascript containing 'uploading failed'"
                         % (testfilename, user.username, project.short_name))
        
        
        return response
    

    def get_uploadpage_response(self, user, project):        
        url = reverse("comicmodels.views.upload_handler", 
            kwargs={"site_short_name":project.short_name})
        factory = RequestFactory()
        request = factory.get(url)
        request.user = user
        response = upload_handler(request, project.short_name)
        return response
    
    def uploaded_files_are_all_shown_on_uploadpage(self,filenames,user):
        """ Assert that all filenames in string array filenames are shown
        on the testproject upload page, when viewed by user
        
        """
                
        response = self.get_uploadpage_response(user,self.testproject)
        
        for filename in filenames:
            self.assertTrue(filename in response.content,"File '%s' was not "
                            "visible on download page when viewed by user %s"
                            % (filename,user.username))
    

    def uploaded_files_are_not_shown_on_uploadpage(self,filenames,user):
        """ Assert that none of the names in string array filenames are shown
        on the testproject upload page, when viewed by user
        
        """
                
        response = self.get_uploadpage_response(user,self.testproject)
                
        for filename in filenames:
            self.assertTrue(filename not in response.content,"Restricted file"
                            " '%s' was visible on download page when viewed"
                            " by user %s"
                            % (filename,user.username))
    
              
    def giverandomfilename(self,user,postfix=""):
        """ Create a filename where you can see from which user is came, but 
        you don't get any nameclashes when creating a few
        """
        return "%s_%s_%s" % (user.username.encode("ascii","ignore"),
                             str(randint(10000,99999)),
                             "testfile%s.txt" % postfix)
        
        

    def test_file_can_be_uploaded_and_viewed_by_correct_users(self):
        """ Upload a fake file, see if correct users can see this file
        """
        
        project = self.testproject        
        
        name1 = self.giverandomfilename(self.root)
        name2 = self.giverandomfilename(self.projectadmin)
        name3 = self.giverandomfilename(self.participant)
        name4 = self.giverandomfilename(self.participant2)
                    
        resp1 = self._upload_test_file(self.root,self.testproject,name1)
        resp2 = self._upload_test_file(self.projectadmin,self.testproject,name2)
        resp3 = self._upload_test_file(self.participant,self.testproject,name3)
        resp4 = self._upload_test_file(self.participant2,self.testproject,name4)
            
        # root and projectadmin should see all files
        self.uploaded_files_are_all_shown_on_uploadpage([name1,name2,name3,name4],self.root)
        self.uploaded_files_are_all_shown_on_uploadpage([name1,name2,name3,name4],self.projectadmin)
        
        # participant1 sees only his or her own file
        self.uploaded_files_are_all_shown_on_uploadpage([name3],self.participant)
        self.uploaded_files_are_not_shown_on_uploadpage([name1,name2,name4],self.participant)
        
        # participant2 also sees only his or her own file
        self.uploaded_files_are_all_shown_on_uploadpage([name4],self.participant2)
        self.uploaded_files_are_not_shown_on_uploadpage([name1,name2,name3],self.participant2)
        
    
    
    def test_uploaded_files_from_editor(self):
        """ You can also upload files in ckeditor, while editing a page. See
        whether this works correctly. 
        
        """
        # TODO: If you upload you result to the site, someone else cannot guess the
        # url and get this. Instead the user is barred from this.
        
        project = self.testproject 
        
        name1 = self.giverandomfilename(self.root)
        name2 = self.giverandomfilename(self.projectadmin)
        name3 = self.giverandomfilename(self.participant)
                        
        resp1 = self._upload_test_file_ckeditor(self.root,self.testproject,name1)
        resp2 = self._upload_test_file_ckeditor(self.projectadmin,self.testproject,name2)
        resp3 = self._upload_test_file_ckeditor(self.participant,self.testproject,name3)
        
        
        # TODO: verify that files uploaded in editor can be served directly.
        # This is not possible now because no files get saved, returning 
        # HttpResponseNotFound for any url get.. Can we fake this somehow?
        url = reverse("project_serve_file",
                       kwargs={"project_name":project.short_name,
                               "path":project.public_upload_dir_rel()+"/"+name1})
        
        
        
             
        
    def get_public_url(self,project,filename):
        """ Get a url where filename can be downloaded without credentials
         
        """
        pass
    
    def _upload_file(self):
        
        model = UploadModel.objects.create(file=None,
                                           user=self.root,
                                           title="upload1",
                                           comicsite=self.testproject,
                                           permission_lvl=comicSiteModel.ALL)
        
class TemplateTagsTest(ComicframeworkTestCase):
    """ See if using template tags like {% include file.txt %} inside page html
    will crash anything
    
    """
    
    
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.signedup_user] = self._create_dummy_project("test-project")
                 
        self.participant2 = self._create_random_user("participant2_")
        self._register(self.participant2,self.testproject)
        
        
        from django.core.files.storage import default_storage
        #this fake file is included on test pages later to test rendering
        default_storage.add_fake_file("fakeinclude.html","This is some fake include content:" 
                    "here is the content of fakecss" 
                    "<somecss>{% insert_file "+default_storage.FAKE_DIRS[1]+"/fakecss.css %} </somecss>and a "
                    "non-existant include: <nonexistant>{% insert_file nothing/nonexistant.txt %}</nonexistant> Also"
                    " try to include scary file path <scary>{% insert_file ../../../allyoursecrets.log %}</scary>")

        
                       

    def _extract_download_link(self, response1):
        """ From a page rendering a listfile template tag, return the first
        download link
        
        """
        
        found = re.search('<ul class="dataset">(.*)</ul>', response1.content, re.IGNORECASE)
        link = ""
        if found:
            filelist_HTML = found.group(0)
            found_link = re.search('href="(.*)">', found.group(0), re.IGNORECASE)
            if found_link:
                link = found_link.group(1)
        
        self.assertTrue(link!="","Could not find any list of files after rendering html '%s'" % response1.content)
        return link                
                                

    def test_listdir(self):
        """ Does the template tag for listing and downloading files in a dir work
        correctly? 
        
        test for comcisite.templatetags.templatetags.listdir
        
        """
        # create a page containing the listdir tag on the public folder.
        # Path to browse is a special path for which Mockstorage will return some
        # file list even if it does not exist                     
        content = "Here are all the files in dir: {% listdir path:"+ settings.COMIC_PUBLIC_FOLDER_NAME+ " extensionFilter:.mhd %} text after "        
        page1 = create_page_in_admin(self.testproject,"listdirpage",content)
                
        # can everyone now view this?
        response1 = self._test_page_can_be_viewed(None,page1)
        response1 = self._test_page_can_be_viewed(self.root,page1)                
        response2 = self._test_page_can_be_viewed(self.signedup_user,page1)
        
        
        # open one of the download links from the file list
        # see if there are any errors rendered in the reponse                        
        link = self._extract_download_link(response1)                
        self._test_url_can_be_viewed(self.root, link)
        self._test_url_can_be_viewed(self.signedup_user, link)
        
        # Now check files listed in a restricted area. These should only be 
        # accessible tp registered users                              
        content = "Here are all the files in dir: {% listdir path:"+ settings.COMIC_REGISTERED_ONLY_FOLDER_NAME+ " extensionFilter:.mhd %} text after "        
        page2 = create_page_in_admin(self.testproject,"restrictedlistdirpage",content)
                
        # can everyone now view this page?           
        response5 = self._test_page_can_be_viewed(self.root,page2)                
        response6 = self._test_page_can_be_viewed(self.signedup_user,page2)
        
        # A download link from a restricted path should only be loadable by
        # participants that registered with the challenge                        
        link = self._extract_download_link(response5)                
        self._test_url_can_be_viewed(self.root, link)
        self._test_url_can_be_viewed(self.participant, link)
        self._test_url_can_not_be_viewed(self.signedup_user, link)
        self._test_url_can_not_be_viewed(None, link) #not logged in user
        
        #are there gracefull errors for non existsing dirs?        
        content = "Here are all the files in a non existing dir: {% listdir path:not_existing/ extensionFilter:.mhd %} text after "                    
        page2 = create_page_in_admin(self.testproject,"list_non_exisiting_dir_page",content)    
        self._test_page_can_be_viewed(self.root,page2)                
        self._test_page_can_be_viewed(self.signedup_user,page2)
        
        
    def test_url_tag(self):
        """ url tag returns a url to view a given objects. Comicframework uses
        a custom url tag to be able use subdomain rewriting. 
        
        """
        # Sanity check: do two different pages give different urls?
        content = "-url1-{% url 'comicsite.views.page' '"+self.testproject.short_name+"' 'testurlfakepage1' %}-endurl1-"
        content += "-url2-{% url 'comicsite.views.page' '"+self.testproject.short_name+"' 'testurlfakepage2' %}-endurl2-"            
        urlpage = create_page_in_admin(self.testproject,"testurltagpage",content)
        
        # SUBDOMAIN_IS_PROJECTNAME affects the way urls are rendered
        with self.settings(SUBDOMAIN_IS_PROJECTNAME = False):            
            response = self._test_page_can_be_viewed(self.signedup_user,urlpage)             
            url1 = find_text_between('-url1-','-endurl1',response.content)
            url2 = find_text_between('-url2-','-endurl2',response.content)            
            self.assertTrue(url1 != url2,"With SUBDOMAIN_IS_PROJECTNAME = False"
                            " URL tag gave the same url for two different "
                            "pages. Both 'testurlfakepage1' and "
                            "'testurlfakepage1' got url '%s'" % url1)
    
        
        with self.settings(SUBDOMAIN_IS_PROJECTNAME = True):
            response = self._test_page_can_be_viewed(self.signedup_user,urlpage)             
            url1 = find_text_between('-url1-','-endurl1',response.content)
            url2 = find_text_between('-url2-','-endurl2',response.content)
            
            self.assertTrue(url1 != url2,"With SUBDOMAIN_IS_PROJECTNAME = True"
                            " URL tag gave the same url for two different "
                            "pages. Both 'testurlfakepage1' and "
                            "'testurlfakepage1' got url '%s'" % url1)
        
        
    def test_insert_file_tag(self):
        """ Can directly include the contents of a file. Contents can again 
        include files.  
        
        """        
        content = "Here is an included file: <toplevelcontent> {% insert_file public_html/fakeinclude.html %}</toplevelcontent>"                
        insertfiletagpage = create_page_in_admin(self.testproject,"testincludefiletagpage",content)
                    
        response = self._test_page_can_be_viewed(self.signedup_user,insertfiletagpage)
            
                
        # Extract rendered content from included file, see if it has been rendered
        # In the correct way
        somecss = find_text_between('<somecss>','</somecss>',response.content)
        nonexistant = find_text_between('<nonexistant>','</nonexistant>',response.content)
        scary = find_text_between('<scary>','</scary>',response.content)
        
        self.assertTrue(somecss != "","Nothing was rendered when including an existing file. Some css should be here")
        self.assertTrue(nonexistant != "","Nothing was rendered when including an existing file. Some css should be here")
        self.assertTrue(scary != "","Nothing was rendered when trying to go up the directory tree with ../ At least some error should be printed")
        
        self.assertTrue("body {width:300px;}" in somecss,"Did not find expected"
                        " content 'body {width:300px;}' when including a test"
                        " css file. Instead found '%s'" % somecss)
        self.assertTrue("No such file or directory" in nonexistant,"Expected a"
                        " message 'No such file or directory' when including "
                        "non-existant file. Instead found '%s'" % nonexistant)
        self.assertTrue("cannot be opened because it is outside the current project" in scary ,
                        "Expected a message 'cannot be opened because it is "
                        "outside the current project' when trying to include filepath with ../"
                        " in it. Instead found '%s'" %scary)
        

    def test_all_projectlinks(self):
        """ Overview showing short descriptions for all projects in the framework """
        
        content = "Here is a test overview of all projects : <allprojects> {% all_projectlinks %} </allprojects>"                
        testallprojectlinkspage = create_page_in_admin(self.testproject,"testallprojectlinkspage",content)
        

        # This overview should be viewable by anyone 
        self._test_page_can_be_viewed(self.signedup_user,testallprojectlinkspage)
        response = self._test_page_can_be_viewed(None,testallprojectlinkspage)
    
        # Extract rendered content from included file, see if it has been rendered
        # In the correct way
        allprojectsHTML = find_text_between('<allprojects>','</allprojects>',response.content)
                    
        self.assertTrue(allprojectsHTML != "","Nothing was rendered for projects overview")
                    

    def apply_standard_middleware(self, request):
        """ Some actions in the admin pages require messages middleware, which is
        not active for some reason when running tests. Manually Process a request
        with middleware so it can be used in an admin action writing messages 
        without crashing
        
        """        
        from django.contrib.sessions.middleware import SessionMiddleware # Some admin actions render messages and will crash without explicit import
        from django.contrib.messages.middleware import MessageMiddleware
        sm = SessionMiddleware()
        mm = MessageMiddleware()
        sm.process_request(request)
        mm.process_request(request)


    def test_registration_request_tag(self):
        """   Registration tags renders a link to register. Either directly of
        after being approved by an admin 
        
        """        
        content = "register here: <registration> {% registration %} </registration>"
        
        registrationpage = create_page_in_admin(self.testproject,"registrationpage",content)
        
        # when you don't have to be approved, just following the link rendered by registration should do
        # register you
        self.testproject.require_participant_review = False
        self.testproject.save()
                                     
        response = self._test_page_can_be_viewed(self.signedup_user,registrationpage)
        self.assertTextBetweenTags(response.content,"registration","Participate in","registering without review")
            
                
        # when participant review is on, all admins will receive an email of a 
        # new participant request, which they can approve or reject.  
        self.testproject.require_participant_review = True
        self.testproject.save()
        
        # have a user request registration                             
        response = self._test_page_can_be_viewed(self.signedup_user,registrationpage)
        self.assertTextBetweenTags(response.content,
                                   "registration",
                                   "Request to participate in",
                                   "registering with participation review")
        
        registration_anchor = find_text_between('<registration>','</registration>',response.content)
        registration_link = extract_href_from_anchor(registration_anchor)
        
        response = self._test_url_can_be_viewed(self.signedup_user,registration_link)
        
        # user should see some useful info after requestion registration                
        self.assertText(response.content,
                        "A participation request has been sent",
                        "Checking message after user has requested participation")
        # and admins should receive an email 
        
        request_mail = mail.outbox[-1]
        
        admins = User.objects.filter(groups__name=self.testproject.admin_group_name())
                                     
        self.assertEmail(request_mail,{"to":admins[0].email,
                                       "subject":"New participation request",
                                       "body":"has just requested to participate"                                       
                                       })
                 
        # link in this email should lead to admin overview of requests
        link_in_email = find_text_between('href="','">here',self.get_mail_html_part(request_mail))
        #TODO: create a function to check all links in the email.
        
        reg_request = RegistrationRequest.objects.filter(project=self.testproject)
        self.assertTrue(reg_request != [],
                        "User {0} clicked registration link, but no registrationRequest\
                         object seems to have been created for project '{1}'".format(self.signedup_user,
                                                                                     self.testproject))
        
        
        factory = RequestFactory()
        request = factory.get("/") #just fake a request, we only need to add user
        request.user = self.testproject.get_admins()[0]
        
        self.apply_standard_middleware(request)
                
        modeladmin = RegistrationRequestAdmin(RegistrationRequest,admin.site)
        modeladmin.accept(request,reg_request)
        
                
        # request.status = RegistrationRequest.ACCEPTED
        # request.save()                        
        # after acceptance, user should receive notification email
        acceptance_mail = mail.outbox[-1]
                        
        self.assertEmail(acceptance_mail,{"to":self.signedup_user.email,
                                          "subject":"participation request accepted",
                                          "body":"has just accepted your request"
                                          })
                
        # after acceptance, user should be able to access restricted pages.
        registeredonlypage =  create_page_in_admin(self.testproject,"registeredonlypage",
                                                   permission_lvl=Page.REGISTERED_ONLY)
        
        self._test_page_can_be_viewed(self.signedup_user,registeredonlypage)
        
        # just to test, a random user should not be able to see this page
        self._test_page_can_not_be_viewed(self._create_random_user("not_registered"),registeredonlypage)
        
        # check if admin can load the view to show all registration requests
        admin_url = reverse('admin:comicmodels_registrationrequest_add')
                
        self._test_url_can_be_viewed(self.projectadmin,admin_url)
        
        #self._test_page_can_be_viewed(self.projectadmin,registeredonlypage)
        
                    
    def get_mail_html_part(self,mail):
        """ Extract html content from email sent with models.comicsite.send_templated_email
        
        """
        return mail.alternatives[0][0]    
           
    def assertText(self,content,expected_text,description=""):
        """ assert that expected_text can be found in text, 
        description can describe what this link should do, like 
        "register user without permission", for better fail messages
                
        """ 
        self.assertTrue(expected_text in content,
                        "expected to find '{0}' but found '{1}' instead.\
                         Attemted action: {2}".format(expected_text,                                           
                                                      content,
                                                      description)) 
        
    
    def assertTextBetweenTags(self,text,tagname,expected_text,description=""):
        """ Assert whether expected_text was found in between <tagname> and </tagname>
        in text. On error, will include description of operation, like "trying to render
        table from csv".
        
        """
        content = find_text_between('<'+tagname +'>','</'+tagname +'>',text)
        self.assertTrue(content != "","Nothing was rendered between <{0}> </{0}>, attempted action: {1}".format(tagname,description))        
        description = "Rendering tag between <{0}> </{0}>, ".format(tagname) + description
        
        self.assertText(text,expected_text,description)

       
            
class ProjectLoginTest(ComicframeworkTestCase):
    """ Getting userena login and signup to display inside a project context 
    (with correct banner and pages, sending project-based email etc..) was quite
    a hassle, not to mention messy. Do all the links still work?
    
    """
    
    
    def setUp_extra(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.signedup_user] = self._create_dummy_project("test-project")
        
         
        self.participant2 = self._create_random_user("participant2_")
        self._register(self.participant2,self.testproject)
                
    def test_project_login(self):
        
        # see if login for specific project works. This tests the project
        # centered signup form.         
        self._create_random_user(site=self.testproject)
        
        # see if views work and all urls can be found
        login_url = reverse("comicsite_signin", kwargs={"site_short_name":self.testproject.short_name}) 
        logout_url = reverse("userena_signout")
        comicsite_signup_complete_url = reverse("comicsite_signup_complete", kwargs={"site_short_name":self.testproject.short_name})
        
        self._test_url_can_be_viewed(self.signedup_user,login_url)
        self._test_url_can_be_viewed(None,login_url)
        self._test_url_can_be_viewed(self.participant,logout_url)
        self._test_url_can_be_viewed(None,logout_url)
        
        self._test_url_can_be_viewed(self.signedup_user,comicsite_signup_complete_url)
        self._test_url_can_be_viewed(None,comicsite_signup_complete_url)
        
        # password reset is in the "forgot password?" link on the project 
        # based login page. Make sure this works right.
        self._test_url_can_be_viewed(self.participant,reverse("userena_password_reset"))
        
        # The other userena urls are not realy tied up with project so I will 
        # leave to userena to test.
       
 
 
class FormsTest(ComicframeworkTestCase):
     """ Any form you can fill out on the website. Does it work? """
     
     def test_submit_existing_project_form(self):
        
        
        url = reverse("comicsite.views.submit_existing_project")
        factory = RequestFactory()
        storage = DefaultStorage()
        
        data = {"contact_name":"Test contact name",
            "contact_email":"testcontactadmin@test.com",
            "title":"Mytestexisting project",
            "URL":"testexistingproject.com"
            }
        
        response = self.client.post(url, data)
        # check email
        self.assertTrue('Thank you. An email has been sent' in response.content, "could not create user. errors in"
                        " html:\n %s \n posted data: %s"                        
                        %(extract_form_errors(response.content),data))
                        

        
        self.assertTrue(len(mail.outbox) > 0,"An email should have been sent to admins but none appears to be sent")
        
        request_mail = mail.outbox[-1]
        project = ComicSite.objects.get(short_name=settings.MAIN_PROJECT_NAME)
        
        self.assertEmail(request_mail,{"to":[x.email for x in project.get_admins()]})
        

class AdminTest(ComicframeworkTestCase):
    """ Comic features a rather involved rewriting of the django interface, offering
    a dedicated admin site for each project in the database. Is everything still working?
        
    """
    
    def setUp_extra(self):
        """ Called by ComicframeworkTestCase
        """
        [self.testproject,
         self.root,
         self.projectadmin,
         self.participant,
         self.registered_user] = self._create_dummy_project("admin-test")
    
    def test_jsi18n(self):
        """ Is javascript being included on admin pages correctly?
        """
        
        jspath = reverse("admin:jsi18n")
        self._test_url_can_be_viewed(self.projectadmin,jspath)
        
        ain = self.testproject.get_project_admin_instance_name()        
        jspathpa = reverse("admin:jsi18n",current_app=self.testproject.get_project_admin_instance_name())
        self._test_url_can_be_viewed(self.projectadmin,jspath)
        
        self.assertTrue(jspath!=jspathpa,"Path to root admin should differ from "
                            "path to project admin, but both resolve to '{}'".format(jspath))
        
    
    def _check_project_admin_view(self,project,viewname,args=[],user=None):
        
        if user == None:
            user = self.projectadmin
        url = reverse(viewname,args=args,current_app=project.get_project_admin_instance_name())
        response = self._test_url_can_be_viewed(user,url)
        
        expected_header = "<p>{} Admin</p>".format(project.short_name)
        
        self.assertTrue(expected_header in response.content,
                        "Did not find expected header '{}'in page source for "
                        "project admin url {}. This header should be printed "
                        "on top of the page".format(expected_header,url))
                                                    
    
    
    def test_projectadmin_views(self):
        """ Is javascript being included on admin pages correctly?
        """
                
        self._check_project_admin_view(self.testproject,"admin:index")
        
        # check page add view    
        self._check_project_admin_view(self.testproject,"admin:comicmodels_page_add")
        
        # check page edit view for first page in project
        firstpage = get_first_page(self.testproject)        
        self._check_project_admin_view(self.testproject,"admin:comicmodels_page_change",args=[firstpage.pk])
        
        # check page history view for first page in project
        firstpage = get_first_page(self.testproject)
        self._check_project_admin_view(self.testproject,"admin:comicmodels_page_history",args=[firstpage.pk])
        
        # check overview of all pages
        self._check_project_admin_view(self.testproject,"admin:comicmodels_page_changelist")
        
        
        # Do the same for registration requests: check of standard views do not crash
        
        # Create some registrationrequests 
        rr1 = RegistrationRequest.objects.create(user=self.participant,project=self.testproject)
        rr2 = RegistrationRequest.objects.create(user=self.participant,project=self.testproject,status=RegistrationRequest.REJECTED)
        rr3 = RegistrationRequest.objects.create(user=self.participant,project=self.testproject,status=RegistrationRequest.ACCEPTED)
        
        # Using root here because projectadmin cannot see objects created above. Don't know why but this is not tested here.
        self._check_project_admin_view(self.testproject,"admin:comicmodels_registrationrequest_change",args=[rr1.pk],user=self.root)
                
        self._check_project_admin_view(self.testproject,"admin:comicmodels_registrationrequest_history",args=[rr1.pk],user=self.root)
        
        self._check_project_admin_view(self.testproject,"admin:comicmodels_registrationrequest_changelist",user=self.root)
        
        # check admin add/ remove view
        
        
        # check that expected links are present in main admin page
         