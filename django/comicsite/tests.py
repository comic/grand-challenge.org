"""
This contains tests using the unittest module. These will pass
when you run "manage.py test.


"""
import pdb
import re
from random import choice

from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib import admin
from django.contrib.auth.models import User


from comicmodels.models import Page,ComicSite
from comicsite.admin import ComicSiteAdmin,PageAdmin
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
    """ Create a ComicSite object as if created through django admin interface.
    
    """
    site = ComicSite.objects.create(short_name=short_name,
                             description=description)
    site.save()
    
    # because we are creating a ComicSite directly, some methods from admin
    # are not being called as they should. Do this manually
    ad = ComicSiteAdmin(ComicSite,admin.site)        
    url = reverse("admin:comicmodels_comicsite_add")                
    factory = RequestFactory()
    request = factory.get(url)
    request.user = user            
    ad.set_base_permissions(request,site)
    
    return site
    

                  
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
    
        

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """ Tests that 1 + 1 always equals 2.
        
        """
        self.assertEqual(1 + 1, 2)


class ViewsTest(TestCase):
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.'
                                     'EmailBackend')
    
    #use fast, non-safe password hashing to speed up testing
    @override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.'
                                        'SHA1PasswordHasher',))
    
    def setUp(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # Create three types of users that exist: Root, can do anything, 
        # Siteadmin, cam do things to a site he or she owns. And logged in
        # user 
        
        self.root = User.objects.create_user('root',
                                        'w.s.kerkstra@gmail.com',
                                        'testpassword')        
        self.root.is_staff = True
        self.root.is_superuser = True
        self.root.save()
        
        # non-root users are created as if they signed up through the site,
        # to maximize test coverage.        
        self.registered_user = self._create_user({"username":"registered_user"})
                                        
        self.siteadmin = self._create_user({"username":"siteadmin",
                                            "email":"df@rt.com"}) 
                    
        self.testsite = create_comicsite_in_admin(self.siteadmin,"viewtest")                
        create_page_in_admin(self.testsite,"testpage1")
        create_page_in_admin(self.testsite,"testpage2")
                
        
    
    def test_registered_user_can_create_project(self):
        """ A user freshly registered through the site can immediately create
        a project
        
        """
        user = self._create_user({"username":"user2","email":"ab@cd.com"})
        testsite = create_comicsite_in_admin(user,"user1project")                
        testpage1 = create_page_in_admin(testsite,"testpage1")
        testpage2 = create_page_in_admin(testsite,"testpage2")
        
        self._test_page_can_be_viewed(user.username,testpage1)
        self._test_page_can_be_viewed(self.root.username,testpage1)
        
        
    
    def test_page_permissions_view(self):
        """ Test that the permissions page does not crash: for root
        https://github.com/comic/comic-django/issues/180 
        
        """
        
        testpage1 = Page.objects.filter(title='testpage1')
        self.assert_(testpage1.exists(),"could not find page 'testpage1'")                 
        url = reverse("admin:comicmodels_page_permissions",
                      args=[testpage1[0].pk])
        
        self._test_url_can_be_viewed(self.root.username,url)
        
        otheruser = self._create_random_user()
        self._test_url_cannot_be_viewed(otheruser.username,url)
        
        
    
    def test_page_change_view(self):
        """ Root can see a page 
        
        """
        user = self._create_user({"username":"user3","email":"de@cd.com"})
        testsite = create_comicsite_in_admin(user,"user3project")                
        testpage1 = create_page_in_admin(testsite,"testpage1")
        testpage2 = create_page_in_admin(testsite,"testpage2")                         
        url = reverse("admin:comicmodels_page_change",
                      args=[testpage1.pk])
        
        self._test_url_can_be_viewed(user.username,url)        
        self._test_url_can_be_viewed(self.root.username,url)
        
        

    def _test_page_can_be_viewed(self,username,page):
        page_url = reverse('comicsite.views.page',
                           kwargs={"site_short_name":page.comicsite.short_name,
                                   "page_title":page.title})
        
        self._test_url_can_be_viewed(username,page_url)
        
                         
    def _test_url_can_be_viewed(self,username,url):
        self._login(username)
        response = self.client.get(url)        
        self.assertEqual(response.status_code, 200, "could not load page"
                         "'%s' logged in as user '%s'"% (url,username))
    
    def _test_url_cannot_be_viewed(self,username,url):
        self._login(username)
        response = self.client.get(url)        
        self.assertNotEqual(response.status_code, 200, "could load restricted " 
                            "page'%s' logged in as user '%s'"% (url,username))
       
    def _signup_user(self,overwrite_data={}):
        """Create a user in the same way as a new user is signed up on the site.
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
                'website':'testwebsite',
                'comicsite':'testcomicwebsite'}
        
        data.update(overwrite_data) #overwrite any key in default if in data
        
        
        signin_page = self.client.post(reverse("userena.views.signup"),data)
                
        # check whether signin succeeded. If succeeded the response will be a
        # httpResponseRedirect object, which has a 'Location' key in its
        # items(). Don't know how to better check for type here.
        list = [x[0] for x in signin_page.items()]
        
        
        self.assertTrue('Location' in list, "could not create user. errors in"
                        " html:\n %s \n posted data: %s"                        
                        %(extract_form_errors(signin_page.content),data))
                        
        
        
    def _create_random_user(self):
        """ Sign up a user, saves me having to think of a unique name each time 
        """
        
        username = "".join([choice('AEOUY')+choice('QWRTPSDFGHHKLMNB') for x in range(3)])
        
        data = {'username':username,
                'email':username+"@test.com"}
        
        return self._create_user(data)

    def _create_user(self,data):
        """ Sign up user in a way as close to production as possible. Check a 
        lot of stuff
        
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
     

    def _login(self,username,password="testpassword"):
        """ convenience function. log in user an assert whether it worked
        
        """
        self.client.logout()
        success = self.client.login(username=username,password=password)
        self.assertTrue(success, "could not log in as user "+username)        
        
    
    
    
        