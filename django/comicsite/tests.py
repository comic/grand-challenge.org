"""
This contains tests using the unittest module. These will pass
when you run "manage.py test.


"""
import pdb
import re
from random import choice

from django.contrib import admin
from django.contrib.auth.models import User
from django.core import mail
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

from comicmodels.models import Page,ComicSite,UploadModel,ComicSiteModel
from comicmodels.views import upload_handler
from comicsite.admin import ComicSiteAdmin,PageAdmin
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
    
        

def create_comicsite_in_admin(user,short_name,description="test project"):
    """ Create a comicsite object as if created through django admin interface.
    
    """
    project = ComicSite.objects.create(short_name=short_name,
                             description=description)
    project.save()
    
    # because we are creating a comicsite directly, some methods from admin
    # are not being called as they should. Do this manually
    ad = ComicSiteAdmin(project,admin.site)        
    url = reverse("admin:comicmodels_comicsite_add")                
    factory = RequestFactory()
    request = factory.get(url)
    request.user = user            
    ad.set_base_permissions(request,project)
    
    return project
    

                  
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
    
        

class ComicframeworkTestCase(TestCase):
    """ Contains methods for creating users using comicframework interface
    """ 
        
    def _test_page_can_be_viewed(self,user,page):
        page_url = reverse('comicsite.views.page',
                           kwargs={"site_short_name":page.comicsite.short_name,
                                   "page_title":page.title})
        
        self._test_url_can_be_viewed(user,page_url)
        
                         
    def _test_url_can_be_viewed(self,user,url):
        self._login(user)
        response = self.client.get(url)        
        self.assertEqual(response.status_code, 200, "could not load page"
                         "'%s' logged in as user '%s'"% (url,user))
    
    def _test_url_cannot_be_viewed(self,user,url):
        self._login(user)
        response = self.client.get(url)        
        self.assertNotEqual(response.status_code, 200, "could load restricted " 
                            "page'%s' logged in as user '%s'"% (url,
                                                                user.username))
       
    def _signup_user(self,overwrite_data={}):
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
        
        
        signin_page = self.client.post(reverse("userena.views.signup"),data)
                
        # check whether signin succeeded. If succeeded the response will be a
        # httpResponseRedirect object, which has a 'Location' key in its
        # items(). Don't know how to better check for type here.
        list = [x[0] for x in signin_page.items()]
        
        
        self.assertTrue('Location' in list, "could not create user. errors in"
                        " html:\n %s \n posted data: %s"                        
                        %(extract_form_errors(signin_page.content),data))
                        
        
        
    def _create_random_user(self,startname=""):
        """ Sign up a user, saves me having to think of a unique name each time
        predend startname if given
        """
        
        username = startname + "".join([choice('AEOUY')+
                                        choice('QWRTPSDFGHHKLMNB')
                                        for x in range(3)])
        
        data = {'username':username,
                'email':username+"@test.com"}
        
        return self._create_user(data)

    def _create_user(self,data):
        """ Sign up user in a way as close to production as possible. Check a 
        lot of stuff. Data is a dictionary form_field:for_value pairs. Any
        unspecified values are given default values
        
        """        
        username = data['username']
        self._signup_user(data)
        
        
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
     

    def _login(self,user,password="testpassword"):
        """ convenience function. log in user an assert whether it worked
        
        """
        self.client.logout()
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
                    
        self.testproject = create_comicsite_in_admin(self.projectadmin,"viewtest")                
        create_page_in_admin(self.testproject,"testpage1")
        create_page_in_admin(self.testproject,"testpage2")
                
        
    
    def test_registered_user_can_create_project(self):
        """ A user freshly registered through the project can immediately create
        a project
        
        """
        user = self._create_user({"username":"user2","email":"ab@cd.com"})
        testproject = create_comicsite_in_admin(user,"user1project")                
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
        testproject = create_comicsite_in_admin(user,"user3project")                
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
        self.testproject = create_comicsite_in_admin(self.projectadmin,"testproject")                
        create_page_in_admin(self.testproject,"testpage1")
        
        # user which has pressed the register link for the project, so is 
        # part of testproject_participants group
        self.participant = self._create_random_user("participant_")
        self._test_register(self.participant,self.testproject)
        
        self.participant2 = self._create_random_user("participant2_")
        self._test_register(self.participant2,self.testproject)
                
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
        
        
    def _test_register(self,user,project):
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
        

    def _upload_test_file(self, user, project,testfilename=""):
        """ Upload a very small text file as user to project
        
        """        
        
        if testfilename == "":
            testfilename = self.givefilename(user)
            
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
        
        # see if there are any errors rendered in the reponse
        errors = re.search('<ul class="errorlist">(.*)</ul>',
                            response.content,
                             re.IGNORECASE)
        if errors:
            self.assertFalse(errors,"Error uploading file '%s':\n %s"
                           %(testfilename, errors.group(1))
                           )
        
        
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
    
              
    def givefilename(self,user):
        return user.username.encode("ascii","ignore") + "_testfile.txt"
        
        

    def test_file_can_be_uploaded_and_viewed_by_correct_users(self):
        """ Upload a fake file, see if correct users can see this file
        """
        
        project = self.testproject        
        
        name1 = self.givefilename(self.root)
        name2 = self.givefilename(self.projectadmin)
        name3 = self.givefilename(self.participant)
        name4 = self.givefilename(self.participant2)
                    
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
        
    
    def _upload_file(self):
        
        model = UploadModel.objects.create(file=None,
                                           user=self.root,
                                           title="upload1",
                                           comicsite=self.testproject,
                                           permission_lvl=comicSiteModel.ALL)
        
        
        
    
    def test_anonymous_and_non_member_user_cannot_see_files(self):
        pass
    
    def test_project_admin_and_root_can_see_all_files(self):
        pass
        
    def test_registered_user_can_see_only_owned_files(self):
        pass
     
    
    
    
    
        
    

    