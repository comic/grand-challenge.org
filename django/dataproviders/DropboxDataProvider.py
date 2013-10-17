import pdb
import re
import os

from django.core.files.storage import FileSystemStorage

from bs4 import BeautifulSoup

from dropbox import client, rest, session
from dropbox.session import DropboxSession
from dropbox.client import DropboxClient
from dropbox.rest import ErrorResponse




class DropboxDataProvider():
    """
    read and write files in a remote dropbox uing the dropbox API 
    """

    def __init__(self, app_key, app_secret, access_type, access_token, access_token_secret,
                  location='',):
        session = DropboxSession(app_key, app_secret, access_type)        
        session.set_token(access_token, access_token_secret)
        self.client = DropboxClient(session)
        self.account_info = self.client.account_info()
        self.location = location
        self.base_url = 'http://dl.dropbox.com/u/{uid}/'.format(**self.account_info)


    def read(self, filename):
        return self.client.get_file(filename).read()


class HtmlLinkReplacer():
    """ replaces links in html. Used to keep links working when including dropbox .html files in pages
        Uses BeautifulSoup html parser.
    """
    
    def __init__(self):
        pass
    
    def replace_links(self,html,baseURL,currentpath):
        """ prepend baseURL to all relative links in <a> and <img> element in html
        
        Keyword arguments:
        html                 -- string with html content
        baseURL              -- prepend to each link, cannot be traversed up 
        currentpath          -- path to prepend, this can be traversed up by links using ../
        """
        soup = BeautifulSoup(html)
        soup = self.replace_a(soup,baseURL,currentpath)
        soup = self.replace_img(soup,baseURL,currentpath)
              
        return soup.renderContents()
    
    def replace_a(self,soup,baseURL,currentpath):                
        for a in soup.findAll('a'):
            if a.has_key('href'):
              a['href'] = self.replace_url(a['href'],baseURL,currentpath)        
        return soup
        
    def replace_img(self,soup,baseURL,currentpath):                
        for a in soup.findAll('img'):
            if a.has_key('src'):
                a['src'] = self.replace_url(a['src'],baseURL,currentpath)
        
        return soup
    
    def replace_url(self,url,baseURL,currentpath):
        """ replace any link like href="/image/img1.jpg" by prepending baseURL
        and currentpath. BaseURL cannot be travesed upward, so it is always prepended
        regardles of the url requested (../../../file) will not end up outside this URL.
        currentpath can be travesed upward by ../  
        
        handles root-relative url (e.g "/admin/index.html") and regular relative url
        (e.g. "images/test.png") correctly   
        """
        
        
        # leave absolute links alone
        if re.match('http://',url) or re.match('https://',url):
              pass
                        
        # for root-relative links 
        elif re.match('/',url): 
              url = baseURL + url
        
        # regular relative links
        elif re.match('\w',url): # match matches start of string, \w = any alphanumeric
              url = baseURL + currentpath + url
        
        
            
        # go up path if ../ are in link
        else:            
            if currentpath.endswith("/"):
                currentpath = currentpath[:-1] #remove trailing slash to make first path.dirname actually go
                                               #up one dir 
            #while re.match('\.\.',url):
                # remove "../"                
             #   url = url[3:]
                # go up one in currentpath                
              #  if currentpath == "":
               #     pass # going up the path would go outside COMIC dropbox bounds. TODO: maybe
                         # throw some kind of outsidescope error?
                #else:    
                 #   currentpath = os.path.dirname(currentpath)
                            
            if currentpath.endswith("/") :
                pass
            else:
                if not currentpath == "":
                    currentpath = currentpath + "/"
            url =  baseURL + currentpath + url
        
        
         
        url = url.replace("//","/") # remove double slashes because this can mess up django's url system
        url = re.sub("http:/(?=\w)","http://",url) # but this also removes double slashes in http://.  Reverse this.
                
        
        return url
              
              
        
        
def LocalDropboxDataProvider(FileSystemStorage):
    """ For storing files in local folder which is synched with comicsiteframework dropbox account    
    """
    pass