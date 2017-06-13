import logging
import os
import re

from bs4 import BeautifulSoup

logger = logging.getLogger("django")


class HtmlLinkReplacer:
    """ replaces links in html. Used to keep links working when including dropbox .html files in pages
        Uses BeautifulSoup html parser.
    """

    def __init__(self):
        pass

    def replace_links(self, html, baseURL, currentpath):
        """ prepend baseURL to all relative links in <a> and <img> element in html
        
        Keyword arguments:
        html                 -- string with html content
        baseURL              -- prepend to each link, cannot be traversed up 
        currentpath          -- path to prepend, this can be traversed up by links using ../
        """
        soup = BeautifulSoup(html, "html.parser")
        soup = self.replace_a(soup, baseURL, currentpath)
        soup = self.replace_img(soup, baseURL, currentpath)

        return soup.renderContents()

    def replace_a(self, soup, baseURL, currentpath):
        for a in soup.findAll('a'):
            a = self.fix_url(a, baseURL, currentpath)
        return soup

    def replace_img(self, soup, baseURL, currentpath):
        for a in soup.findAll('img'):
            a = self.fix_url(a, baseURL, currentpath)
        return soup

    def refers_to_file(self, url):

        (start, ext) = os.path.splitext(url)
        if ext:
            return True
        else:
            return False

    def get_url(self, a):

        if a.has_attr('src'):
            return a['src']
        elif a.has_attr('href'):
            return a['href']
        else:
            return ""

    def fix_url(self, a, baseURL, currentpath):
        """ Only rewrite links to files, links to paths are never an included
        file and just be used as is. 
        """

        url = self.get_url(a)

        if url and self.refers_to_file(url):
            return self.replace_url(a, baseURL, currentpath)

        else:
            return a

    def replace_url(self, a, baseURL, currentpath):
        """ problem I am trying to solve: Files from the projects file folder can
        be included. These included files can have links in them to other files 
        in file folder, or to other pages on comic. Desiderata:
        
        * Html files in a folder structure in the file folder should work as
        expected, with relative, absolute and relative absolute links.
        
        * Security should remain: there should be no way to serve any file or 
        content if the project's organizer does not want this. 
                        
        Solution:
        We need to treat file urls and page urls differently.                 
        * Each file in a projects file folder,  (anything with an extension),  
        
        
        
        replace any link like href="/image/img1.jpg" by prepending baseURL
        and currentpath. BaseURL cannot be travesed upward, so it is always prepended
        regardles of the url requested (../../../file) will not end up outside this URL.
        currentpath can be travesed upward by ../  
        
        handles root-relative url (e.g "/admin/index.html") and regular relative url
        (e.g. "images/test.png") correctly   
        """

        if a.has_attr('src'):
            url = a['src']
        elif a.has_attr('href'):
            url = a['href']
        else:
            raise AttributeError("Trying to replace a link which has no src and no href"
                                 "attribute. This should never happen.")

        # leave absolute links alone
        if re.match('http://', url) or re.match('https://', url):
            pass

        # for root-relative links
        elif re.match('/', url):
            url = baseURL + url

        # regular relative links
        elif re.match('\w', url):  # match matches start of string, \w = any alphanumeric
            url = baseURL + currentpath + url


        # go up path if ../ are in link
        else:
            if currentpath.endswith("/"):
                currentpath = currentpath[:-1]  # remove trailing slash to make first path.dirname actually go
                # up one dir
                # while re.match('\.\.',url):
                # remove "../"
                #   url = url[3:]
                # go up one in currentpath
                #  if currentpath == "":
                #     pass # going up the path would go outside COMIC dropbox bounds. TODO: maybe
                # throw some kind of outsidescope error?
                # else:
                #   currentpath = os.path.dirname(currentpath)

            if currentpath.endswith("/"):
                pass
            else:
                if not currentpath == "":
                    currentpath = currentpath + "/"
            url = baseURL + currentpath + url

        url = url.replace("//", "/")  # remove double slashes because this can mess up django's url system
        url = re.sub("http:/(?=\w)", "http://", url)  # but this also removes double slashes in http://.  Reverse this.

        if a.has_attr('src'):
            a['src'] = url
        elif a.has_attr('href'):
            a['href'] = url
        else:
            logger.warning("Trying to replace a link which has no src and no href"
                           "attribute. This should never happen.")
            pass

        return a
