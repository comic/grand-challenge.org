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
from comicmodels.models import Page,ComicSite,UploadModel,ComicSiteModel
from comicmodels.views import upload_handler
from comicsite.admin import ComicSiteAdmin,PageAdmin
from comicsite.storage import MockStorage
from django.core.files.storage import DefaultStorage
from comicsite.views import _register
from profiles.admin import UserProfileAdmin
from profiles.models import UserProfile
from profiles.forms import SignupFormExtra


def get_or_create_user(username,password):
    query_result = User.objects.filter(username=username)
    if query_result.exists():
        return query_result[0]
        
    else:
        return 
    
                  
def create_page_in_admin(comicsite,title,content="testcontent"):
    """ Create a Page object as if created through django admin interface.
    
    """
    page_admin = PageAdmin(Page,admin.site)
    page = Page.objects.create(title=title,
                               comicsite=comicsite,
                               html=content,
                               permission_lvl=Page.ALL)
    page_admin.first_save(page)
    return page
    
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
        found = re.search(start+'(.*)'+end,haystack,re.IGNORECASE)
        return found.group(1)    


        

class ComicframeworkTestCase(TestCase):
    """ Contains methods for creating users using comicframework interface
    """ 
    
    
    def _register(self,user,project):
        """ Register user for the given project, follow actual signup as
        closely as possible.
        """
        url = reverse("comicsite.views._register", 
            kwargs={"site_short_name":self.testproject.short_name})
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
        
        
                         
    def _test_url_can_be_viewed(self,user,url):
        response,username = self._view_url(user,url)                    
        self.assertEqual(response.status_code, 200, "could not load page"
                         "'%s' logged in as user '%s'"% (url,user))
        return response
    
    def _test_url_cannot_be_viewed(self,user,url):        
        response,username = self._view_url(user,url)
        self.assertNotEqual(response.status_code, 200, "could load restricted " 
                            "page'%s' logged in as user '%s'"% (url,
                                                                username))
        return response
    
    def _find_errors_in_page(self, response):    
        """ see if there are any errors rendered in the html of reponse.
        Used for checking forms 
        
        """
        errors = re.search('<ul class="errorlist">(.*)</ul>', 
            response.content, 
            re.IGNORECASE)
        return errors
    
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
        validationlink_result = re.search('/example.com(.*)\n',
                                          validation_mail.body,
                                          re.IGNORECASE)
        
        self.assertTrue(validationlink_result, "could not find any link in" 
                        "registration email")
        
        validationlink = validationlink_result.group(1)        
        response = self.client.get(validationlink)        
        
        self.assertEqual(self.client.get('/accounts/'+username+'/').status_code,
                         200,"Could not access user account after using" 
                         "validation link!")
            
        
        query_result = User.objects.filter(username=username)        
        return query_result[0] 

    def create_comicsite_in_admin(self,user,short_name,description="test project"):
        """ Create a comicsite object as if created through django admin interface.
        
        """
        #project = ComicSite.objects.create(short_name=short_name,
                                # description=description,
                                # header_image=settings.COMIC_PUBLIC_FOLDER_NAME+"fakefile2.jpg")
        #project.save()
        
        # because we are creating a comicsite directly, some methods from admin
        # are not being called as they should. Do this manually
        #ad = ComicSiteAdmin(project,admin.site)        
        url = reverse("admin:comicmodels_comicsite_add")                
        factory = RequestFactory()
        
        
        storage = DefaultStorage()
        header_image = storage._open(settings.COMIC_PUBLIC_FOLDER_NAME+"/fakefile2.jpg") 
        data = {"short_name":short_name,
                "description":description,
                "logo":"fakelogo.jpg",               
                "header_image": header_image,
                "prefix":"form",
                "page_set-TOTAL_FORMS": u"0",
                "page_set-INITIAL_FORMS": u"0",
                "page_set-MAX_NUM_FORMS": u""            
                }
        
        
        success = self._login(user)
        
        response = self.client.post(url,data)
        errors = self._find_errors_in_page(response)        
        if errors:
            self.assertFalse(errors, "Error creating project '%s':\n %s" % (short_name, errors.group(0)))
                
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


# =============================================================================
# Decorators applied to the ComicframeworkTestCase class: see 
# https://docs.djangoproject.com/en/1.4/topics/testing/#django.test.utils.override_settings

#don't send real emails, keep them in memory
ComicframeworkTestCase = override_settings(EMAIL_BACKEND='django.core.mail.'
                                         'backends.locmem.EmailBackend'
                                         )(ComicframeworkTestCase)
                                        
#use fast, non-safe password hashing to speed up testing
ComicframeworkTestCase = override_settings(PASSWORD_HASHERS=('django.contrib.'
                                           'auth.hashers.SHA1PasswordHasher',)
                                           )(ComicframeworkTestCase)
                                          
#Use a fake storage provider which does not save anything to disk.
ComicframeworkTestCase = override_settings(DEFAULT_FILE_STORAGE = 
                                           "comicsite.storage.MockStorage"
                                           )(ComicframeworkTestCase)




class ViewsTest(ComicframeworkTestCase):
        
    def setUp(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # Create three types of users that exist: Root, can do anything, 
        # projectadmin, cam do things to a project he or she owns. And logged in
        # user 
        
        self.root = User.objects.create_user('root',
                                        'w.s.kerkstra@gmail.com',
                                        'testpassword')        
        self.root.is_staff = True
        self.root.is_superuser = True
        self.root.save()
        
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage.        
        
        self.registered_user = self._create_random_user("registered_")
                                        
        self.projectadmin = self._create_random_user("projectadmin_")
                    
        self.testproject = self.create_comicsite_in_admin(self.projectadmin,"viewtest")                
        create_page_in_admin(self.testproject,"testpage1")
        create_page_in_admin(self.testproject,"testpage2")
                
        
    
    def test_registered_user_can_create_project(self):
        """ A user freshly registered through the project can immediately create
        a project
        
        """
        user = self._create_user({"username":"user2","email":"ab@cd.com"})
        testproject = self.create_comicsite_in_admin(user,"user1project")                
        testpage1 = create_page_in_admin(testproject,"testpage1")
        testpage2 = create_page_in_admin(testproject,"testpage2")
                
        self._test_page_can_be_viewed(user,testpage1)
        self._test_page_can_be_viewed(self.root,testpage1)
        
        
    
    def test_page_permissions_view(self):
        """ Test that the permissions page does not crash: for root
        https://github.com/comic/comic-django/issues/180 
        
        """
        
        testpage1 = Page.objects.filter(title='testpage1')
        self.assert_(testpage1.exists(),"could not find page 'testpage1'")                 
        url = reverse("admin:comicmodels_page_permissions",
                      args=[testpage1[0].pk])
        
        self._test_url_can_be_viewed(self.root,url)
        
        otheruser = self._create_random_user("other_")
        self._test_url_cannot_be_viewed(otheruser,url)
        
        
    
    def test_page_change_view(self):
        """ Root can see a page 
        
        """
        user = self._create_user({"username":"user3","email":"de@cd.com"})
        testproject = self.create_comicsite_in_admin(user,"user3project")                
        testpage1 = create_page_in_admin(testproject,"testpage1")
        testpage2 = create_page_in_admin(testproject,"testpage2")                         
        url = reverse("admin:comicmodels_page_change",
                      args=[testpage1.pk])
        
        self._test_url_can_be_viewed(user,url)        
        self._test_url_can_be_viewed(self.root,url)
        
                
    
    
class UploadTest(ComicframeworkTestCase):
    
    
    def setUp(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # Create four types of users that exist: Root, can do anything, 
        # projectadmin, cam do things to a project he or she owns. Participant can
        # show some restricted content for a project and upload files,
        # signup_user can see some pages but not others.
        
        self.root = User.objects.create_user('root',
                                      'w.s.kerkstra@gmail.com',
                                      'testpassword')        
        self.root.is_staff = True
        self.root.is_superuser = True
        self.root.save()
        
        
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage. 
               
        # Creator of a project.                                        
        self.projectadmin = self._create_random_user("projectadmin_")
        
        # The project created by projectadmin 
        self.testproject = self.create_comicsite_in_admin(self.projectadmin,"testproject")                
        create_page_in_admin(self.testproject,"testpage1")
        
        # user which has pressed the register link for the project, so is 
        # part of testproject_participants group
        self.participant = self._create_random_user("participant_")
        self._register(self.participant,self.testproject)
        
        self.participant2 = self._create_random_user("participant2_")
        self._register(self.participant2,self.testproject)
                
        # user which has only registered at comicframework but has not 
        # registered for any project
        self.signedup_user = self._create_random_user("signedup_user_")
        
        
        
           
    
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
    
              
    def giverandomfilename(self,user):
        """ Create a filename where you can see from which user is came, but 
        you don't get any nameclashes when creating a few
        """
        return "%s_%s_%s" % (user.username.encode("ascii","ignore"),
                             str(randint(10000,99999)),
                             "testfile.txt")
        
        

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
    
    
    def setUp(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # Create four types of users that exist: Root, can do anything, 
        # projectadmin, cam do things to a project he or she owns. Participant can
        # show some restricted content for a project and upload files,
        # signup_user can see some pages but not others.
        
        self.root = User.objects.create_user('root',
                                      'w.s.kerkstra@gmail.com',
                                      'testpassword')        
        self.root.is_staff = True
        self.root.is_superuser = True
        self.root.save()
        
        
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage. 
               
        # Creator of a project.                                        
        self.projectadmin = self._create_random_user("projectadmin_")
        
        # The project created by projectadmin 
        self.testproject = self.create_comicsite_in_admin(self.projectadmin,"testproject")                
        create_page_in_admin(self.testproject,"testpage1")
        
        # user which has pressed the register link for the project, so is 
        # part of testproject_participants group
        self.participant = self._create_random_user("participant_")
        self._register(self.participant,self.testproject)
        
        self.participant2 = self._create_random_user("participant2_")
        self._register(self.participant2,self.testproject)
                
        # user which has only registered at comicframework but has not 
        # registered for any project
        self.signedup_user = self._create_random_user("signedup_user_")
    
        

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
        self._test_url_cannot_be_viewed(self.signedup_user, link)
        self._test_url_cannot_be_viewed(None, link) #not logged in user
        
        
        
        
        
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
            
            
class ProjectLoginTest(ComicframeworkTestCase):
    """ Getting userena login and signup to display inside a project context 
    (with correct banner and pages, sending project-based email etc..) was quite
    a hassle, not to mention messy.  Do all the links still work?
    
    """
    
    
    def setUp(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # Create four types of users that exist: Root, can do anything, 
        # projectadmin, cam do things to a project he or she owns. Participant can
        # show some restricted content for a project and upload files,
        # signup_user can see some pages but not others.
        
        self.root = User.objects.create_user('root',
                                      'w.s.kerkstra@gmail.com',
                                      'testpassword')        
        self.root.is_staff = True
        self.root.is_superuser = True
        self.root.save()
        
        
        # non-root users are created as if they signed up through the project,
        # to maximize test coverage. 
               
        # Creator of a project.                                        
        self.projectadmin = self._create_random_user("projectadmin_")
        
        # The project created by projectadmin 
        self.testproject = self.create_comicsite_in_admin(self.projectadmin,"testproject")                
        create_page_in_admin(self.testproject,"testpage1")
        
        # user which has pressed the register link for the project, so is 
        # part of testproject_participants group
        self.participant = self._create_random_user("participant_")
        self._register(self.participant,self.testproject)
        
        self.participant2 = self._create_random_user("participant2_")
        self._register(self.participant2,self.testproject)
                
        # user which has only registered at comicframework but has not 
        # registered for any project
        self.signedup_user = self._create_random_user("signedup_user_")
        
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
        
        
        
        
        
    
        
        
    
    
        
        
        
        
        
        
