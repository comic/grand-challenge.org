"""
This contains tests using the unittest module. These will pass
when you run "manage.py test.


"""
import pdb

from django.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.contrib.auth.models import User

from comicmodels.models import Page,ComicSite
from comicsite.admin import ComicSiteAdmin,PageAdmin



def login_as_root_user(testcase):
    """ log in comicmodels.tests.ViewsTest object testcase as admin. Assert 
    whether login was successful. Convenience function to save a few lines of 
    code.  
    
    """
    user = get_or_create_root_user()
    success = testcase.client.login(username='root',password='rootpassword')
    testcase.assertTrue(success,"logging in as root failed")
    return user


def get_or_create_root_user():
    query_result = User.objects.filter(username='root')
    if query_result.exists():
        return query_result[0]
        
    else:
        user = User.objects.create_user('root',
                                    'w.s.kerkstra@gmail.com',
                                    'rootpassword')
    
        user.is_staff = True
        user.is_superUser = True
        user.save()
        return user

                  
 
class SimpleTest(TestCase):
    def test_basic_addition(self):
        """ Tests that 1 + 1 always equals 2.
        
        """
        self.assertEqual(1 + 1, 2)


class ViewsTest(TestCase):
            
    def setUp(self):
        """ Create some objects to work with
        """
        testsite = ComicSite.objects.create(short_name="viewtest",
                                 description="project for automated view test")
        testsite.save()
        
        # because we are creating a ComicSite directly, some methods from admin
        # are not being called as they should. Do this manually
        ad = ComicSiteAdmin(testsite,admin.site)        
        url = reverse("admin:comicmodels_comicsite_add")
        factory = RequestFactory()
        request = factory.get(url)        
        root = login_as_root_user(self)
        request.user = root        
        ad.set_base_permissions(request,testsite)
        
        

        testpage1 = Page.objects.create(title="testpage1",
                                        comicsite=testsite,
                                        html="testpage1 content",
                                        permission_lvl=Page.ALL)
        
        testpage2 = Page.objects.create(title="testpage2",
                                        comicsite=testsite,
                                        html="testpage2 content",
                                        permission_lvl=Page.REGISTERED_ONLY) 
        
        #fake adding pages through page admin, to set permissions 
        page_admin = PageAdmin(testsite,admin.site)
        page_url = reverse("admin:comicmodels_page_add")        
        page_admin.first_save(testpage1)
        page_admin.first_save(testpage2)
        
        #crate 
    
    def _test_as_root(self,url):
        """ Log in as root and try to load url, will assert whether this works 
        
        """   
                         
        login_as_root_user(self)            
        response = self.client.get(url)                        
        self.assertEqual(response.status_code, 200, "loading %s as root "
                        "failed, full response was %s" % (url,response.content))
                        
    
    def test_page_permissions_view(self):
        """ Test that the permissions page does not crash:
        https://github.com/comic/comic-django/issues/180 
        
        """
        
        testpage1 = Page.objects.filter(title='testpage1')
        self.assert_(testpage1.exists(),"could not find page 'testpage1'")                 
        url = reverse("admin:comicmodels_page_permissions",
                      args=[testpage1[0].pk])
        self._test_as_root(url)
                        
    
    