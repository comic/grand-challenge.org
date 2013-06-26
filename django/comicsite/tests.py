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




def get_or_create_root_user(username,password):
    query_result = User.objects.filter(username=username)
    if query_result.exists():
        return query_result[0]
        
    else:
        user = User.objects.create_user(username,
                                    'w.s.kerkstra@gmail.com',
                                    password)
    
        user.is_staff = True
        user.is_superUser = True
        user.save()
        return user


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
    

 
class SimpleTest(TestCase):
    def test_basic_addition(self):
        """ Tests that 1 + 1 always equals 2.
        
        """
        self.assertEqual(1 + 1, 2)


class ViewsTest(TestCase):
            
    def setUp(self):
        """ Create some objects to work with
        """
        root = get_or_create_root_user("root","rootpassword")
        
        testsite = create_comicsite_in_admin(root,"viewtest")                
        create_page_in_admin(testsite,"testpage1")
        create_page_in_admin(testsite,"testpage2")
        
         


    def _login_as_root_user(self):
        """ log in comicmodels.tests.ViewsTest object testcase as admin. Assert 
        whether login was successful. Convenience function to save a few lines of 
        code.  
    
        """        
        success = self.client.login(username='root',password='rootpassword')    
        return success

    
    
    def _test_as_root(self,url):
        """ Log in as root and try to load url, will assert whether this works 
        
        """   
                         
        self._login_as_root_user()            
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
 
    
    