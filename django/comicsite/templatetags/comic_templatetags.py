"""
Custom tags to use in templates or code to render file lists etc.

 History
 03/09/2012    -     Sjoerd    -    Created this file

"""

import pdb
import csv, numpy
import datetime
import ntpath
import os
import random
import re
import string
import StringIO
import sys
import traceback
import logging
from collections import Counter

from exceptions import Exception
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas




from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist,ImproperlyConfigured
from django.core.urlresolvers import NoReverseMatch
from django.contrib.auth.models import Group, User, Permission
from profiles.models import UserProfile
from django.core.files.storage import DefaultStorage
from django.template import RequestContext, defaulttags
from django.utils.html import escape
from profiles.forms import SignupFormExtra

from comicmodels.models import FileSystemDataset, UploadModel, DropboxFolder  # FIXME: abstract Dataset should be imported here, not explicit filesystemdataset. the template tag should not care about the type of dataset.
from comicmodels.models import ComicSite, Page
import comicsite.views
from dropbox.rest import ErrorResponse
from dataproviders import FileSystemDataProvider
from dataproviders.DropboxDataProvider import DropboxDataProvider, HtmlLinkReplacer  # TODO: move HtmlLinkReplacer to better location..
from dataproviders.ProjectExcelReader import ProjectExcelReader


#---------#---------#---------#---------#---------#---------#---------#---------
# This is needed to use the @register.tag decorator
#register = template.Library()
from comicsite.templatetags import library_plus
register = library_plus.LibraryPlus()

logger = logging.getLogger("django")


def parseKeyValueToken(token):
    """
    Parses the given token string and returns a parameter dictionary
    \param token A string given by the templatetag which is assumes to look like
    \this:
            visualization key1:value1,key2:value2,...
    \return A dictionary
    """
    split = token.split_contents()
    tag = split[0]
    args = split[1:]
    return dict([param.split(":") for param in args])



def get_usagestr(function_name):
    """
    Return usage string for a registered template tag function. For displaying
    this info in errors or tag overviews
    """
    if register.usagestrings.has_key(function_name):
        usagestr = register.usagestrings["dataset"]
    else:
        usagestr = ""

    return sanitize_django_items(usagestr)


@register.tag(name="taglist",
              usagestr="""
              <% taglist %> :
              show all available tags
                       """
              )
def get_taglist(parser, token):
    return TagListNode()

#=========#=========#=========#=========#=========#=========#=========#=========#=========


def subdomain_is_projectname():
    """ Check whether this setting is true in settings. Return false if not found

    """
    if hasattr(settings,"SUBDOMAIN_IS_PROJECTNAME"):
        subdomain_is_projectname = settings.SUBDOMAIN_IS_PROJECTNAME
        if subdomain_is_projectname and not hasattr(settings,"MAIN_HOST_NAME"):
            msg = """Key 'SUBDOMAIN_IS_PROJECTNAME' was defined in settings,
             but 'MAIN_HOST_NAME' was not. These belong together. Please
             add 'MAIN_HOST_NAME' and set it to the hostname of your site."""
            raise ImproperlyConfigured(msg)
    else:
        subdomain_is_projectname = False

    return subdomain_is_projectname



@register.tag
def url(parser, token):
    """ Overwrite built in url tag. It works identicaly, except that where possible
    it will use subdomains to refer to a project instead of a full url path.

    For example, if the subdomain is vessel12.domain.com it will refer to a page
    'details' as /details/ instead of /site/vessel12/details/

    REQUIREMENTS:
    * MIDDLEWARE_CLASSES in settings should contain
      'comicsite.middleware.subdomain.SubdomainMiddleware'

    * These keys should be in the django settings file:
      SUBDOMAIN_IS_PROJECTNAME = True
      MAIN_HOST_NAME = <your site's hostname>

    * APACHE url rewriting should be in effect to rewrite subdomain to
      site/project/. To get you started: the following apache config does this
      for the domain 'devcomicframework.org'
      (put this in your apache config file)

        RewriteEngine   on
        RewriteCond $1 .*/$
        RewriteCond $1 !^/site/.*
        RewriteCond %{HTTP_HOST} !^devcomicframework\.org$
        RewriteCond %{HTTP_HOST} !^www.devcomicframework\.org$
        RewriteCond %{HTTP_HOST} ^([^.]+)\.devcomicframework\.org$
        RewriteRule (.*) /site/%1$1 [PT]


    TODO: turn on and off this behaviour in settings, maybe explicitly define
    base domain to also make it possible to use dots in the base domain.

    """

    orgnode = defaulttags.url(parser,token)
    return comic_URLNode(orgnode.view_name,orgnode.args, orgnode.kwargs, orgnode.asvar)

class comic_URLNode(defaulttags.URLNode):

    def render(self, context):

        # TODO: How to refer to method in this file nicely? This seems a bit cumbersome
        subdomain_is_projectname = comicsite.templatetags.comic_templatetags.subdomain_is_projectname()

        #get the url the default django method would give.
        url = super(comic_URLNode, self).render(context)


        url = url.lower()

        if subdomain_is_projectname:
            if hasattr(context['request'],"subdomain"):
                subdomain = context['request'].subdomain
            else:
                subdomain = ""

            if subdomain == "":
                #we are on the regular domain, do not change any links
                return url
            else:
                # Interpret subdomain as a comicsite. What would normally be the
                # path to this comicsite?


                path_to_site = reverse("comicsite.views.site",args=[subdomain]).lower()

                if url.startswith(path_to_site):
                    return url.replace(path_to_site,"/")
                else:
                    # this url cannot use the domain name shortcut, so it is
                    # probably meant as a link the main comicframework site.
                    # in that case hardcode the domain to make sure the sub-
                    # domain is gone after following this link
                    return settings.MAIN_HOST_NAME + url
        else:
            return url




class TagListNode(template.Node):
    """ Print available tags as text
    """

    def __init__(self):
        pass

    def render(self, context):
        html_out = "<table class =\"comictable taglist\">"

        html_out = html_out + "<tr><th>tagname</th><th>description</th></tr>"
        rowclass = "odd"
        for key,val in register.usagestrings.iteritems():
            html_out = html_out + "<tr class=\"%s\"><td>%s</td><td>%s</td></tr>\
                    " %(rowclass, key, sanitize_django_items(val))
            if rowclass == "odd":
                rowclass = "even"
            else:
                rowclass = "odd"

        html_out = html_out + "</table>"

        return html_out

def sanitize_django_items(string):
    """
    remove {{,{% and other items which would be rendered as tags by django
    """
    out = string
    out = out.replace("{{","&#123;&#123;")
    out = out.replace("}}","&#125;&#125;")
    out = out.replace("{%","&#123;&#37;")
    out = out.replace("%}","&#37;&#125;")
    out = out.replace(">","&#62;")
    out = out.replace("<","&#60;")
    out = out.replace("\n","<br/>")
    return out


@register.simple_tag
def metafooterpages():
    """ Get html for links to general pages like 'contact' """
    html_string = "<div class='text'><span>COMIC:</span></div>"
    pages = comicsite.views.getPages(settings.MAIN_PROJECT_NAME)
    for p in pages:
        if not p.hidden:
            url = reverse('comicsite.views.comicmain', kwargs={'page_title':p.title})
            if comicsite.templatetags.comic_templatetags.subdomain_is_projectname():
                url = settings.MAIN_HOST_NAME + url
            html_string += "<a class='metaFooterMenuItem' href='%s'>" % url
            html_string += p.display_title == "" and p.title or p.display_title
            html_string += "</a>"
    return html_string


@register.tag(name="filelist")
def do_get_files(parser, token):

    try:
        # split_contents() knows not to split quoted strings.
        tag_name, filefolder = token.split_contents()
        format_string = "\"%Y-%m-%d %I:%M %p\""
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    if not (format_string[0] == format_string[-1] and format_string[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)
    return FileListNode(format_string[1:-1], filefolder[1:-1])


class FileListNode(template.Node):
    """ Show list of files in given dir
    """

    def __init__(self, format_string, filefolder):
        self.format_string = format_string
        self.filefolder = filefolder


    def render(self, context):
        dp = FileSystemDataProvider.FileSystemDataProvider(self.filefolder)
        images = dp.getImages()

        htmlOut = "available files:" + ", ".join(images)
        return htmlOut



#========#========#========#========#========#========#========#========
@register.tag(name="dataset",
              usagestr= """Tag usage: {% dataset <datasetname>,<comicsitename> %}. <comicsitename> can be\
                  omitted, defaults to current site"""
              )
def render_dataset(parser, token):
    """ Given a challenge and a dataset name, show all files in this dataset as list"""

    #usagestr = DatasetNode.usagestr
    usagestr = get_usagestr("render_dataset")

    # check some basic stuff
    try:
        tag_name, args = token.split_contents()
    except ValueError:
        errormsg = "Error rendering {% " + token.contents + " %}: tag requires at least one \
                    argument. " + usagestr
        # raise template.TemplateSyntaxError(errormsg)
        return TemplateErrorNode(errormsg)

    if args.count(",") == 0:
        dataset_title = args
        project_name = ""
    elif args.count(",") == 1 :
        dataset_title, project_name = args.split(",")
    else:
        errormsg = "Error rendering {% " + token.contents + " %}: found " + str(args.count(",")) + \
                    " comma's, expected at most 1." + usagestr
        return TemplateErrorNode(errormsg)


    return DatasetNode(dataset_title, project_name)


class DatasetNode(template.Node):
    """ Show list of linked files for given dataset
    """

    usagestr = """{% dataset <datasetname>,<comicsitename> %}
                  Tag usage: {% dataset <datasetname>,<comicsitename> %}. <comicsitename> can be\
                  omitted, defaults to current site"""

    def __init__(self, dataset_title, project_name):
        self.dataset_title = dataset_title
        self.project_name = project_name


    def make_dataset_error_msg(self, msg):
        errormsg = "Error rendering DataSet '" + self.dataset_title + "' for project '" + self.project_name + "': " + msg
        return makeErrorMsgHtml(errormsg)

    def render(self, context):

        if self.project_name == "":
            self.project_name = context.page.comicsite.short_name

        try:
            dataset = FileSystemDataset.objects.get(comicsite__short_name=self.project_name, title=self.dataset_title)

        except ObjectDoesNotExist as e:
           return self.make_dataset_error_msg("could not find object in database")

        else:
            self.filefolder = dataset.get_full_folder_path()


        dp = FileSystemDataProvider.FileSystemDataProvider(self.filefolder)

        try:
              filenames = dp.getAllFileNames()
        except (OSError) as e:

          return self.make_dataset_error_msg(str(e))


        links = []
        for filename in filenames:

            downloadlink = reverse('filetransfers.views.download_handler_dataset_file', kwargs={'project_name':dataset.comicsite.short_name,
                                                                                            'dataset_title':dataset.title,
                                                                                            'filename':filename})
            # <a href="{% url filetransfers.views.download_handler_dataset_file project_name='VESSEL12' dataset_title='vessel12' filename='test.png' %}">test </a>
            links.append("<li><a href=\"" + downloadlink + "\">" + filename + " </a></li>")

        description = dataset.description
        htmlOut = description + "<ul class=\"dataset\">" + "".join(links) + "</ul>"

        return htmlOut


@register.tag(name="listdir",
              usagestr= """Tag usage: {% listdir path:string  extensionFilter:ext1,ext2,ext3 %}

              path: directory relative to this projects dropbox folder to list files from. Do not use leading slash.
              extensionFilter: An include filter to specify the file types which should be displayd in the filebrowser.
              """
              )
def listdir(parser, token):
    """ show all files in dir as a downloadable list"""

    usagestr = get_usagestr("listdir")

    try:
        args = parseKeyValueToken(token)
    except ValueError:
        errormsg = "Error rendering {% " + token.contents + " %}: Error parsing token. " + usagestr
        return TemplateErrorNode(errormsg)


    if "path" not in args.keys():
        errormsg = "Error rendering {% " + token.contents + " %}: dataset argument is missing." + usagestr
        return TemplateErrorNode(errormsg)

    return ListDirNode(args)


class ListDirNode(template.Node):
    """ Show list of linked files for given directory
    """

    usagestr = get_usagestr("listdir")

    def __init__(self, args):
        self.path = args['path']
        self.args = args


    def make_dataset_error_msg(self, msg):
        errormsg = "Error listing folder '" + self.path + "': " + msg
        return makeErrorMsgHtml(errormsg)

    def render(self, context):

        project_name = context.page.comicsite.short_name
        projectpath = project_name + "/" + self.path
        storage = DefaultStorage()

        try:
            filenames = storage.listdir(projectpath)[1]

        except OSError as e:
            return self.make_dataset_error_msg(str(e))


        # if extensionsFilter is given,  show only filenames with those extensions
        if 'extensionFilter' in self.args.keys():
            extensions = self.args['extensionFilter'].split(",")
            filtered = []
            for extension in extensions:

                filtered = filtered + [f for f in filenames if f.endswith(extension)]
            filenames = filtered

        links = []
        for filename in filenames:

            downloadlink = reverse('project_serve_file',
                                    kwargs={'project_name':project_name,
                                            'path':self.path+"/"+filename})

            links.append("<li><a href=\"" + downloadlink + "\">" + filename + " </a></li>")


        htmlOut = "<ul class=\"dataset\">" + "".join(links) + "</ul>"

        return htmlOut


@register.tag(name = "visualization")
def render_visualization(parser, token):
    """ Given a dataset name, show a 2D visualization for that """

    usagestr = """Tag usage: {% visualization dataset:string
                                              width:number
                                              height:number
                                              deferredLoad:0|1
                                              extensionFilter:ext1,ext2,ext3%}
                  The only mandatory argument is dataset.
                  width/heigth: Size of the 2D view area.
                  defferedLoad: If active, user has to click on the area to load the viewer.
                  extensionFilter: An include filter to specify the file types which should be displayd in the filebrowser.
                  """
    try:
        args = parseKeyValueToken(token)
    except ValueError:
        errormsg = "Error rendering {% " + token.contents + " %}: Error parsing token. " + usagestr
        return TemplateErrorNode(errormsg)

    if "dataset" not in args.keys():
        errormsg = "Error rendering {% " + token.contents + " %}: dataset argument is missing." + usagestr
        return TemplateErrorNode(errormsg)

    return VisualizationNode(args)

class VisualizationNode(template.Node):
    """
    Renders the ComicWebWorkstation using MeVisLab
    """

    def __init__(self, args):
        self.args = args

    def make_dataset_error_msg(self, msg):
        errormsg = "Error rendering Visualization '" + str(self.args) + ":" + msg
        return makeErrorMsgHtml(errormsg)

    def render(self, context):
        htmlOut = """

          <div class="COMICWebWorkstationButtons">
              <button id="comicViewerSetSmallSize%(id)d"> small </button>
              <button id="comicViewerSetLargeSize%(id)d"> large </button>
              <button id="comicViewerFullscreenToggle%(id)d"> fullscreen </button>
          </div>
          <div id="comicViewer%(id)d" style="width: %(width)spx; height:%(height)spx"></div>
          <script type="text/javascript">
            var fmeViewer%(id)d = null;
            //$(document).ready(function() {
              console.log('fmeviewee')
              fmeViewer%(id)d = new COMICWebWorkstationWrapper("comicViewer%(id)d");
              var options = {'path':'%(path)s',
                             'deferredLoad':%(deferredLoad)s,
                             'extensionFilter':'%(extensionFilter)s',
                             'width':%(width)s,
                             'height':%(height)s,
                             'application': 'COMICWebWorkstation_1.2',
                             'webSocketHostName':%(webSocketHostName)s,
                             'webSocketPort':%(webSocketPort)s,
                             'urlToMLABRoot': "/static/js" };
              fmeViewer%(id)d.init(options);
            //});

            $("#comicViewerSetSmallSize%(id)d").click(function(){
                fmeViewer%(id)d.setSmallSize()
            })
            $("#comicViewerSetLargeSize%(id)d").click(function(){
                fmeViewer%(id)d.setLargeSize()
            })
            $("#comicViewerFullscreenToggle%(id)d").click(function(){
                fmeViewer%(id)d.gotoFullscreen()
            })

          </script>
        """ % ({"id": id(self),
                "width": self.args.get("width", "600"),
                "height": self.args.get("height", "400"),
                "path": self.args.get("dataset"),
                "extensionFilter": self.args.get("extensionFilter", ""),
                "deferredLoad": self.args.get("deferredLoad", "0"),
                "webSocketHostName": self.args.get("webSocketHostName",
                                                    "undefined"),
                "webSocketPort": self.args.get("webSocketPort", "undefined")})
        return htmlOut



@register.tag(name="dropbox")
def render_dropbox(parser, token):
    """ Given a django_dropbox item title, render a file from this dropbox """

    usagestr = """Tag usage: {% dropbox title:string file:filepath %}
                  title: the title of an autorized django_dropbox item
                  file: path to a file in your dropbox /apps/COMIC folder
                  """
    try:
        args = parseKeyValueToken(token)
    except ValueError:
        errormsg = "Error rendering {% " + token.contents + " %}: Error parsing token. " + usagestr
        return TemplateErrorNode(errormsg)

    if "title" not in args.keys():
        errormsg = "Error rendering {% " + token.contents + " %}: title argument is missing." + usagestr
        return TemplateErrorNode(errormsg)

    if "file" not in args.keys():
        errormsg = "Error rendering {% " + token.contents + " %}: file argument is missing." + usagestr
        return TemplateErrorNode(errormsg)

    try:
        df = DropboxFolder.objects.get(title=args['title'])
    except ObjectDoesNotExist as e:
        return TemplateErrorNode("could not find dropbox titled '" + args['title'] + "' in database")

    provider = df.get_dropbox_data_provider()
    replacer = HtmlLinkReplacer()

    return DropboxNode(args, df, provider, replacer)


class DropboxNode(template.Node):
    def __init__(self, args, df, provider, replacer):
        self.args = args
        self.df = df
        self.provider = provider
        self.replacer = replacer

    def make_dropbox_error_msg(self, msg):
        errormsg = "Error rendering dropbox '" + str(self.args) + ": " + msg
        return makeErrorMsgHtml(errormsg)

    def render(self, context):

        try:
            contents = self.provider.read(self.args["file"])
        except ErrorResponse as e:
            return self.make_dropbox_error_msg(str(e))

        # any relative link inside included file has to be replaced to make it work within the COMIC
        # context.
        baseURL = reverse('comicsite.views.dropboxpage', kwargs={'site_short_name':context.page.comicsite.short_name,
                                                                'page_title':context.page.title,
                                                                'dropboxname':self.args['title'],
                                                                'dropboxpath':"remove"})
        # for some reason reverse matching does not work for emtpy dropboxpath (maybe views.dropboxpage
        # throws an error?. Workaround is to add 'remove' as path and chop this off the returned link
        # nice.
        baseURL = baseURL[:-7]  # remove "remove/" from baseURL
        currentpath = ntpath.dirname(self.args['file']) + "/"  # path of currently rendered dropbox file

        replaced = self.replacer.replace_links(contents, baseURL, currentpath)
        htmlOut = replaced

        return htmlOut


def add_quotes(string):
    """ add quotes to string if not there
    """
    if string.startswith("'") or string.startswith("'"):
        return string
    else:
        return "'"+ string +"'"

def strip_quotes(string):
    """ strip outermost quotes from string if there
    """

    stripped = string
    if string.startswith("'") or string.startswith("'"):
        stripped = stripped[1:]
    if string.endswith("'") or string.endswith("'"):
        stripped = stripped[:-1]

    return stripped

def in_list(needles,haystack):
    """ return True if any of the strings in string array needles is in haystack

    """
    for needle in needles:
        if needle in haystack:
            return True
    return False


def inlist(needles,haystack):
    """ Return true if any of the items in list needles is in haystack

    """
    for needle in needles:
        if needle in haystack:
            return True

    return False



# {% insertfile results/test.txt %}
@register.tag(name="insert_file")
def insert_file(parser, token):
    """ Render a file from the local dropbox folder of the current project"""

    usagestr = """Tag usage: {% insertfile <file> %}
                  <file>: filepath relative to project dropboxfolder.
                  Example: {% insertfile results/test.txt %}
                  You can use url parameters in <file> by using {{curly braces}}.
                  Example: {% insterfile {{id}}/result.txt %} called with ?id=1234
                  appended to the url will show the contents of "1234/result.txt".
                  """

    split = token.split_contents()
    tag = split[0]
    all_args = split[1:]

    if len(all_args) != 1:
        error_message = "Expected 1 argument, found " + str(len(all_args))
        return TemplateErrorNode(error_message)
    else:
        args = {}
        filename = all_args[0]
        if inlist(["../","~"],filename):
             error_message = "filename '%s' contains ../ or ~. Going up the directory tree is not allowed." %filename
             return TemplateErrorNode(error_message)

        args["file"] = add_quotes(filename)

    replacer = HtmlLinkReplacer()
    return InsertFileNode(args, replacer, parser)


class InsertFileNode(template.Node):
    def __init__(self, args, replacer,parser):
        self.args = args
        self.replacer = replacer
        self.parser = parser

    def make_error_msg(self, msg):
        errormsg = "Error including file '" + "," + self.args["file"] + "': " + msg
        return makeErrorMsgHtml(errormsg)

    def substitute(self, string, substitutions):
        """
        Take each key in the substitutions dict. See if this key exists
        between double curly braces in string. If so replace with value.

        Example:
        substitute("my name is {{name}}.",{version:1,name=John})
        > "my name is John"
        """

        for key, value in substitutions:
            string = re.sub("{{" + key + "}}", value, string)

        return string

    def replace_links(self, filename, contents, currentpage):
        """Relative urls which work on disk might not
        work properly when used in included file. Make sure any links in contents
        still point to the right place 
        
        """
        
        # any relative link inside included file has to be replaced to make it work within the COMIC
        # context.
        base_url = reverse('comicsite.views.insertedpage', kwargs={'site_short_name':currentpage.comicsite.short_name, 
                                                                   'page_title':currentpage.title, 
                                                                   'dropboxpath':"remove"})
        # for some reason reverse matching does not work for emtpy dropboxpath (maybe views.dropboxpage
        # throws an error?. Workaround is to add 'remove' as path and chop this off the returned link.
        # nice.
        base_url = base_url[:-7] # remove "remove/" from baseURL
        current_path = ntpath.dirname(filename) + "/" # path of currently inserted file
        replaced = self.replacer.replace_links(contents, 
            base_url, 
            current_path)
        html_out = replaced
                
        
        return html_out

    def render(self, context):

        #text typed in the tag 
        token = self.args['file']
        
        # the token (parameter) given to this tag can be one of three types:
        # * a raw filename like "stuff.html" or "results/table1.txt"
        # * a filname containing a variable like "results/{{teamid}}/table1.txt"
        # * a django template variable like "site.short_name"
        
        # Find out what type it is:
        

        # If it contains any / or {{ resolving as django var
        # is going to throw an error. Prevent unneeded exception, just skip
        # rendering as var in that case.
        filename_resolved = ""
        if not in_list(["{","}","\\","/"],token):
            filter = self.parser.compile_filter(strip_quotes(token))
            filename_resolved = filter.resolve(context)

        # if resolved filename is empty, resolution failed, just treat this
        # param as a filepath
        if filename_resolved == "":
            filename = strip_quotes(token)
        else:
            filename = filename_resolved

        # if there are {{}}'s in there, try to substitute this with url
        # parameter given in the url
        filename = self.substitute(filename, context["request"].GET.items())

        # If any {{parameters}} are still in filename they were not replaced.
        # This filename is missing information, show this as error text.
        if re.search("{{\w+}}", filename):

            missed_parameters = re.findall("{{\w+}}", filename)
            found_parameters = context["request"].GET.items()

            if found_parameters == []:
                found_parameters = "None"
            error_msg = "I am missing required url parameter(s) %s, url parameter(s) found: %s "\
                        "" % (missed_parameters, found_parameters)
            return self.make_error_msg(error_msg)


        project_name = context["site"].short_name
        filepath = os.path.join(settings.DROPBOX_ROOT, project_name, filename)

        storage = DefaultStorage()
        try:
            contents = storage.open(filepath, "r").read()
        except Exception as e:
            return self.make_error_msg(str(e))

        # TODO check content safety

        # For some special pages like login and signup, there is no current page
        # In that case just don't try any link rewriting

        # TODO: here confused coding comes to light: I need to have the page
        # object that this template tag is on in order to process it properly.
        # I use both the element .page, added by
        # ComicSiteRequestContext, and a key 'currentpage' added by the view.
        # I think both are not ideal, and should be rewritten so all template
        # tags are implicitly passed page (and project) by default. It think
        # this needs custom template context processors or custom middleware.
        # As a workaround, just checking for both conditions.
        if context.has_key("currentpage"):
            currentpage = context["currentpage"]
        elif hasattr(context,"page"):
            currentpage = context.page
        else:
            currentpage = None
        
        

        if currentpage and os.path.splitext(filename)[1] != ".css":
            html_out = self.replace_links(filename, contents, currentpage)
            # rewrite relative links
        else:
            html_out = contents

        
        return html_out
    
    
    

@register.tag(name="insert_graph")
def insert_graph(parser, token):
    """ Render a csv file from the local dropbox to a graph """

    usagestr = """Tag usage: {% insert_graph <file> type:<type>%}
                  <file>: filepath relative to project dropboxfolder.
                  <type>: how should the file be parsed and rendered? default
                      is to render an FROC curve for a an csv with first column
                      for x and subsequent columns for y, first row for short
                      var names, second row for verbose names.
                  Example: {% insert_graph results/test.txt %}
                  You can use url parameters in <file> by using {{curly braces}}.
                  Example: {% inster_graphfile {{id}}/result.txt %} called with ?id=1234
                  appended to the url will show the contents of "1234/result.txt".
                  """

    split = token.split_contents()
    tag = split[0]
    all_args = split[1:]

    if len(all_args) > 2:
        error_message = "Expected no more than 2 arguments, found " + str(len(all_args))
        return TemplateErrorNode(error_message + "usage: \n" + usagestr)

    else:
        args = {}
        args["file"] = all_args[0]
        if len(all_args) == 2:
            args["type"] = all_args[1].split(":")[1]
        else:
            args["type"] = "csv"  # default



    replacer = HtmlLinkReplacer()

    return InsertGraphNode(args, replacer)


class InsertGraphNode(template.Node):
    def __init__(self, args, replacer):
        self.args = args
        self.replacer = replacer

    def make_error_msg(self, msg):
        errormsg = "Error rendering graph from file '" + "," + self.args["file"] + "': " + msg
        return makeErrorMsgHtml(errormsg)

    def substitute(self, string, substitutions):
        """
        Take each key in the substitutions dict. See if this key exists
        between double curly braces in string. If so replace with value.

        Example:
        substitute("my name is {{name}}.",{version:1,name=John})
        > "my name is John"
        """

        for key, value in substitutions:
            string = re.sub("{{" + key + "}}", value, string)

        return string



    def render(self, context):

        filename_raw = self.args['file']
        filename_clean = self.substitute(filename_raw, context["request"].GET.items())

        # If any url parameters are still in filename they were not replaced. This filename
        # is missing information..
        if re.search("{{\w+}}", filename_clean):

            missed_parameters = re.findall("{{\w+}}", filename_clean)
            found_parameters = context["request"].GET.items()

            if found_parameters == []:
                found_parameters = "None"
            error_msg = "I am missing required url parameter(s) %s, url parameter(s) found: %s "\
                        "" % (missed_parameters, found_parameters)
            return self.make_error_msg(error_msg)

        project_name = context.page.comicsite.short_name
        filename = os.path.join(settings.DROPBOX_ROOT, project_name, filename_clean)

        storage = DefaultStorage()
        try:
            contents = storage.open(filename, "r").read()
        except Exception as e:
            return self.make_error_msg(str(e))

        # TODO check content safety

        # any relative link inside included file has to be replaced to make it work within the COMIC
        # context.
        base_url = reverse('comicsite.views.insertedpage', kwargs={'site_short_name':context.page.comicsite.short_name,
                                                                'page_title':context.page.title,
                                                                'dropboxpath':"remove"})
        # for some reason reverse matching does not work for emtpy dropboxpath (maybe views.dropboxpage
        # throws an error?. Workaround is to add 'remove' as path and chop this off the returned link
        # nice.
        base_url = base_url[:-7]  # remove "remove/" from baseURL
        current_path = ntpath.dirname(filename_clean) + "/"  # path of currently inserted file



        try:
            render_function = getrenderer(self.args["type"])
            # (table,headers) = read_function(filename)
        except Exception as e:
            return self.make_error_msg(str("getrenderer:" + e.message))


        try:
            svg_data = render_function(filename)
        # except Exception as e:
        except:
            raise
            # return self.make_error_msg(str("Error calling render funtion '%s()' : %s" %(render_function.__name__,
             #                                                                           traceback.format_exc(0))))
        # self.get_graph_svg(table,headers)


        # html_out = "A graph rendered! source: '%s' <br/><br/> %s" %(filename_clean,svg_data)
        html_out = svg_data

        # rewrite relative links

        return html_out




#---------#---------#---------#---------#---------#---------#---------#---------

def getrenderer(format):
    """Holds list of functions which can take in a filepath and return html to show a graph.
    By using this function we can easily list all available renderers and provide some safety:
    only functions listed here can be called from the template tag render_graph.
    """
    renderers = {"csv":render_FROC,
               "anode09":render_anode09_result,
               "anode09_table":render_anode09_table, }

    if not renderers.has_key(format):
        raise Exception("reader for format '%s' not found. Available formats: %s" % (format, \
                        ",".join(renderers.keys())))

    return renderers[format]


def get_graph_svg(table, headers):
        """ return svg instructions as string to plot a froc curve of csvfile

        """
        # del table[-1]

        columns = zip(*table)

        fig = Figure(facecolor='white')
        canvas = FigureCanvas(fig)

        for i in range(1, len(columns)):
          fig.gca().plot(columns[0], columns[i], label=headers[i], gid=headers[i])
        fig.gca().set_xlim([10 ** -2, 10 ** 2])
        fig.gca().set_ylim([0, 1])
        fig.gca().legend(loc='best', prop={'size':10})
        fig.gca().grid()
        fig.gca().grid(which='minor')
        fig.gca().set_xlabel('False positives/scan')
        fig.gca().set_ylabel('Sensitivity')

        fig.gca().set_xscale("log")
        fig.set_size_inches(8, 6)

        return canvas_to_svg(canvas)


def canvas_to_svg(canvas):
    """ Render matplotlib canvas as string containing html/svg instructions. These instructions can be
    pasted into any html page and will be rendered as graph by any modern browser.

    """
    imgdata = StringIO.StringIO()
    imgdata.seek(0, os.SEEK_END)

    canvas.print_svg(imgdata, format='svg')

    svg_data = imgdata.getvalue()
    imgdata.close()

    return svg_data



# readers for graph data.
def render_FROC(filename):
    """ Read in csv file with the following format:
        x_value,        all nodules,    peri-fissural nodules, ...N
        0.02,           0.31401,        0.0169492,             ...N

        First column must be x values, subsequent columns can be any number of y
        values, one for each line to plot.
        First column should be header names to return with each column.

        Returns: string containing html/svg instruction to render an FROC curve
        of all the variables found in file
    """

    has_header = True
    table = []
    storage = DefaultStorage()
    f = storage.open(filename, 'r')
    csvreader = csv.reader(f)
    i = 0
    headers = []
    for row in csvreader:
      if not has_header or i > 1:
        for j, cell in enumerate(row):
          row[j] = float(cell)
        table.append(row)
      elif has_header:
        headers = row
        # nonFloatColumns = [x % len(headers) for x in nonFloatColumns]
        # print nonFloatColumns
      i = i + 1
    f.close()

    columns = zip(*table)

    fig = Figure(facecolor='white')
    canvas = FigureCanvas(fig)

    for i in range(1, len(columns)):
      fig.gca().plot(columns[0], columns[i], label=headers[i], gid=headers[i])
    fig.gca().set_xlim([10 ** -2, 10 ** 2])
    fig.gca().set_ylim([0, 1])
    fig.gca().legend(loc='best', prop={'size':10})
    fig.gca().grid()
    fig.gca().grid(which='minor')
    fig.gca().set_xlabel('False positives/image')
    fig.gca().set_ylabel('Sensitivity')

    fig.gca().set_xscale("log")
    fig.set_size_inches(8, 6)

    return canvas_to_svg(canvas)



def render_anode09_result(filename):
    """ Read in a file with the anode09 result format, to be able to read this without
        changing the evaluation executable. anode09 results have the following format:

    <?php
        $x=array(1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,0.02,0.02,0.04,0.06,0.06,0.08,0.08,0.0 etc..
        $frocy=array(0,0.00483092,0.00966184,0.0144928,0.0144928,0.0144928,0.0193237,0.0241546,0.0289855,0.02 etc..
        $frocscore=array(0.135266,0.149758,0.193237,0.236715,0.246377,0.26087,0.26087,0.21187);
        $pleuraly=array(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.0169492,0.0169492,0.0169492,0.016 etc..
        $pleuralscore=array(0.0508475,0.0508475,0.0677966,0.118644,0.135593,0.152542,0.152542,0.104116);
        $fissurey=array(0,0,0,0.0285714,0.0285714,0.0285714,0.0571429,0.0571429,0.0571429,0.0571429,0.0571429 etc..
        $fissurescore=array(0.171429,0.171429,0.285714,0.314286,0.314286,0.314286,0.314286,0.269388);
        $vasculary=array(0,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0. etc..
        $vascularscore=array(0.116279,0.139535,0.186047,0.209302,0.22093,0.244186,0.244186,0.194352);
        $isolatedy=array(0,0,0.0238095,0.0238095,0.0238095,0.0238095,0.0238095,0.047619,0.0714286,0.0714286,0 etc..
        $isolatedscore=array(0.238095,0.261905,0.309524,0.380952,0.380952,0.380952,0.380952,0.333333);
        $largey=array(0,0.0111111,0.0111111,0.0111111,0.0111111,0.0111111,0.0111111,0.0222222,0.0222222,0.022 etc..
        $largescore=array(0.111111,0.122222,0.144444,0.177778,0.177778,0.188889,0.188889,0.15873);
        $smally=array(0,0,0.00854701,0.017094,0.017094,0.017094,0.025641,0.025641,0.034188,0.034188,0.034188, etc..
        $smallscore=array(0.153846,0.17094,0.230769,0.282051,0.299145,0.316239,0.316239,0.252747);
    ?>


        First row are x values, followed by alternating rows of FROC scores for each x value and
        xxxscore variables which contain FROC scores at
        [1/8     1/4    1/2    1     2    4    8    average] respectively and are meant to be
        plotted in a table

        Returns: string containing html/svg instruction to render an anode09 FROC curve
        of all the variables found in file

    """

    # small nodules,large nodules, isolated nodules,vascular nodules,pleural nodules,peri-fissural nodules,all nodules

    vars = parse_php_arrays(filename)
    assert vars != {}, "parsed result of '%s' was emtpy. I cannot plot anything" % filename

    fig = Figure(facecolor='white')
    canvas = FigureCanvas(fig)

    fig.gca().plot(vars["x"], vars["smally"], label="nodules < 5mm", gid="small")
    fig.gca().plot(vars["x"], vars["largey"], label="nodules > 5mm", gid="large")
    fig.gca().plot(vars["x"], vars["isolatedy"], label="isolated nodules", gid="isolated")
    fig.gca().plot(vars["x"], vars["vasculary"], label="vascular nodules", gid="vascular")
    fig.gca().plot(vars["x"], vars["pleuraly"], label="pleural nodules", gid="pleural")
    fig.gca().plot(vars["x"], vars["fissurey"], label="peri-fissural nodules", gid="fissure")
    fig.gca().plot(vars["x"], vars["frocy"], label="all nodules", gid="frocy")


    fig.gca().set_xlim([10 ** -2, 10 ** 2])
    fig.gca().set_ylim([0, 1])
    fig.gca().legend(loc='best', prop={'size':10})
    fig.gca().grid()
    fig.gca().grid(which='minor')
    fig.gca().set_xlabel('Average FPs per scan')
    fig.gca().set_ylabel('Sensitivity')

    fig.gca().set_xscale("log")
    fig.set_size_inches(8, 6)

    return canvas_to_svg(canvas)


#=========#=========#=========#=========#=========#=========#=========#=========#=========
def render_anode09_table(filename):
    """ Read in a file with the anode09 result format and output html for an anode09 table
    anode09 results have the following format:

    <?php
        $x=array(1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,1e-39,0.02,0.02,0.04,0.06,0.06,0.08,0.08,0.0 etc..
        $frocy=array(0,0.00483092,0.00966184,0.0144928,0.0144928,0.0144928,0.0193237,0.0241546,0.0289855,0.02 etc..
        $frocscore=array(0.135266,0.149758,0.193237,0.236715,0.246377,0.26087,0.26087,0.21187);
        $pleuraly=array(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.0169492,0.0169492,0.0169492,0.016 etc..
        $pleuralscore=array(0.0508475,0.0508475,0.0677966,0.118644,0.135593,0.152542,0.152542,0.104116);
        $fissurey=array(0,0,0,0.0285714,0.0285714,0.0285714,0.0571429,0.0571429,0.0571429,0.0571429,0.0571429 etc..
        $fissurescore=array(0.171429,0.171429,0.285714,0.314286,0.314286,0.314286,0.314286,0.269388);
        $vasculary=array(0,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0.0116279,0. etc..
        $vascularscore=array(0.116279,0.139535,0.186047,0.209302,0.22093,0.244186,0.244186,0.194352);
        $isolatedy=array(0,0,0.0238095,0.0238095,0.0238095,0.0238095,0.0238095,0.047619,0.0714286,0.0714286,0 etc..
        $isolatedscore=array(0.238095,0.261905,0.309524,0.380952,0.380952,0.380952,0.380952,0.333333);
        $largey=array(0,0.0111111,0.0111111,0.0111111,0.0111111,0.0111111,0.0111111,0.0222222,0.0222222,0.022 etc..
        $largescore=array(0.111111,0.122222,0.144444,0.177778,0.177778,0.188889,0.188889,0.15873);
        $smally=array(0,0,0.00854701,0.017094,0.017094,0.017094,0.025641,0.025641,0.034188,0.034188,0.034188, etc..
        $smallscore=array(0.153846,0.17094,0.230769,0.282051,0.299145,0.316239,0.316239,0.252747);
    ?>


        First row are x values, followed by alternating rows of FROC scores for each x value and
        xxxscore variables which contain FROC scores at
        [1/8     1/4    1/2    1     2    4    8    average] respectively and are meant to be
        plotted in a table

        Returns: string containing html/svg instruction to render an anode09 FROC curve
        of all the variables found in file

    """

    # small nodules,large nodules, isolated nodules,vascular nodules,pleural nodules,peri-fissural nodules,all nodules

    vars = parse_php_arrays(filename)
    assert vars != {}, "parsed result of '%s' was emtpy. I cannot create table" % filename

    table_id = id_generator()

    tableHTML = """<table border=1 class = "comictable csvtable sortable" id="%s">
        <thead><tr>
            <td class ="firstcol">FPs/scan</td><td align=center width='54'>1/8</td>
            <td align=center width='54'>1/4</td>
            <td align=center width='54'>1/2</td><td align=center width='54'>1</td>
            <td align=center width='54'>2</td><td align=center width='54'>4</td>
            <td align=center width='54'>8</td><td align=center width='54'>average</td>
        </tr></thead>""" % table_id

    tableHTML = tableHTML + "<tbody>"
    tableHTML = tableHTML + array_to_table_row(["small nodules"] + vars["smallscore"])
    tableHTML = tableHTML + array_to_table_row(["large nodules"] + vars["largescore"])
    tableHTML = tableHTML + array_to_table_row(["isolated nodules"] + vars["isolatedscore"])
    tableHTML = tableHTML + array_to_table_row(["vascular nodules"] + vars["vascularscore"])
    tableHTML = tableHTML + array_to_table_row(["pleural nodules"] + vars["pleuralscore"])
    tableHTML = tableHTML + array_to_table_row(["peri-fissural nodules"] + vars["fissurescore"])
    tableHTML = tableHTML + array_to_table_row(["all nodules"] + vars["frocscore"])
    tableHTML = tableHTML + "</tbody>"
    tableHTML = tableHTML + "</table>"

    # FIXME: create a temporary solution to including javascript and css with template tags
    script = """<script type="text/javascript">

                        $('#%s').dataTable({
                            "bJQueryUI": true,
                            "sPaginationType": "full_numbers",
                            "bPaginate": false,
                            "bLengthChange": false,
                            "bFilter": false,
                            "bInfo": false,
                            "bAutoWidth": false
                        });

            </script>""" % table_id


    return "<div class=\"comictablecontainer\">" + tableHTML + "</div>"



def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """ thanks to Ignacio Vazquez-Abrams on stackoverflow"""
    return ''.join(random.choice(chars) for x in range(size))


def array_to_table_row(rowvalues, trclass=""):
    output = "<tr class = \"%s\">" % trclass
    for value in rowvalues:
        if type(value) is float:
            output = output + "<td>%.3f</td>" % (value)
        else:
            output = output + "<td>%s</td>" % (str(value))
    output = output + "</tr>"
    return output

def parse_php_arrays(filename):
    """ Parse a php page containing only php arrays like $x=(1,2,3). Created to parse anode09 eval results.

    Returns: dict{"varname1",array1,....},
    array1 is a float array

    """
    verbose = False

    output = {}

    storage = DefaultStorage()
    with storage.open(filename, 'r') as f:
        content = f.read()
        content = content.replace("\n", "")
        php = re.compile("\<\?php(.*?)\?\>",re.DOTALL)
        phpcontent = php.search(content).group(1)
        assert phpcontent != "" , "could not find anything like <?php ?> in '%s'" % filename

        phpvars = phpcontent.split("$")
        phpvars = [x for x in phpvars if x != '']  # remove empty
        if verbose:
            print "found %d php variables in %s. " % (len(phpvars), filename)
            print "parsing %s into int arrays.. " % (filename)

        # check wheteher this looks like a php var
        phpvar = re.compile("([a-zA-Z]+[a-zA-Z0-9]*?)=array\((.*?)\);",re.DOTALL)
        for var in phpvars:
           result = phpvar.search(var)

           #TODO Log these messages as info
           if result == None :
               msg = "Could not match regex pattern '%s' to '%s'\
                                    " % (phpvar.pattern, var)
               continue


           if len(result.groups()) != 2:
               msg = "Expected to find  varname and content,\
                      but regex '%s' found %d items:%s " % (phpvar.pattern, len(result.groups()),
                                                              "[" + ",".join(result.groups()) + "]")
               continue


           (varname, varcontent) = result.groups()

           output[varname] = [float(x) for x in varcontent.split(",")]

    return output





@register.tag(name="url_parameter")
def url_parameter(parser, token):
    """ Try to read given variable from given url. """

    usagestr = """Tag usage: {% url_parameter <param_name> %}
                  <param_name>: The parameter to read from the requested url.
                  Example: {% url_parameter name %} will write "John" when the
                  requested url included ?name=John.
                  """

    split = token.split_contents()
    tag = split[0]
    all_args = split[1:]

    if len(all_args) != 1:
        error_message = "Expected 1 argument, found " + str(len(all_args))
        return TemplateErrorNode(error_message)
    else:
        args = {}
        args["url_parameter"] = all_args[0]

    args["token"] = token

    return UrlParameterNode(args)


class UrlParameterNode(template.Node):

    def __init__(self, args):
        self.args = args

    def make_error_msg(self, msg):
        errormsg = "Error in url_parameter tag: '" + ",".join(self.args) + "': " + msg
        return makeErrorMsgHtml(errormsg)

    def render(self, context):

        # request= context["request"].GET[]
        if context['request'].GET.has_key(self.args['url_parameter']):
            return context['request'].GET[self.args['url_parameter']]  # FIXME style: is this too much in one line?
        else:
            error_message = "Error rendering %s: Parameter '%s' not found in request URL" % ("{%  " + self.args['token'].contents + "%}",
                                                                                             self.args['url_parameter'])
            return makeErrorMsgHtml(error_message)



@register.tag(name="all_projects")
def render_all_projects(parser, token):
    """ Render an overview of all projects """

    try:
        projects = ComicSite.objects.non_hidden()
    except ObjectDoesNotExist as e:
        errormsg = "Error rendering {% " + token.contents + " %}: Could not find any comicSite object.."
        return TemplateErrorNode(errormsg)

    return AllProjectsNode(projects)

class AllProjectsNode(template.Node):
    """ return html list listing all projects in COMIC
    """

    def __init__(self, projects):
        self.projects = projects

    def render(self, context):
        html = ""
        for project in self.projects:
            html += self.project_summary_html(project)
        return html

    def project_summary_html(self,project):
        if comicsite.templatetags.comic_templatetags.subdomain_is_projectname():
            protocol,domainname = settings.MAIN_HOST_NAME.split("//")
            url = protocol + "//" +project.short_name +"."+ domainname
            return comicsite.views.comic_site_to_html(project,url)
        else:
            return comicsite.views.comic_site_to_html(project)

@register.tag(name="all_projectlinks")
def render_all_projectlinks(parser, token):
    """ Render an overview of all projects including all links to external
    projects and challenges

    """

    try:
        projects = ComicSite.objects.non_hidden()
    except ObjectDoesNotExist as e:
        errormsg = "Error rendering {% " + token.contents + " %}: Could not find any comicSite object.."
        return TemplateErrorNode(errormsg)

    return AllProjectLinksNode(projects)

class AllProjectLinksNode(template.Node):
    """ return html list listing all projects in COMIC
    """

    def __init__(self, projects):
        self.projects = projects

    def render(self, context):
        projectlinks = []

        for project in self.projects:
            projectlinks.append(project.to_projectlink())

        projectlinks += self.read_grand_challenge_projectlinks()


        html = self.project_links_per_year(projectlinks)

        #html = ""
        #for projectlink in projectlinks:
        #    html += projectlink.render_to_html()


        html = "<ul>" + html + "</ul>"

        return html

    def project_links_per_year(self,projectlinks):
        """ Create html to show each projectlink with subheadings per year sorted
        by diminishing year

        """
        #go throught all projectlinks and bin per year

        years = {}

        for projectlink in projectlinks:
            year = projectlink.date.year
            if years.has_key(year):
                years[year].append(projectlink)
            else:
                years[year] = [projectlink]


        years = years.items()
        years = sorted(years,key=lambda x: x[0],reverse=True)

        html = ""
        for year in years:
            html += "<h2 class ='yearHeader' id = '%i'><a class ='yearHeaderAnchor'>%i</a></h2>" % (year[0],year[0])
            html += "\n".join([link.render_to_html() for link in year[1]])

        return html



    def project_summary_html(self,project):

        if comicsite.templatetags.comic_templatetags.subdomain_is_projectname():
            protocol,domainname = settings.MAIN_HOST_NAME.split("//")
            url = protocol + "//" +project.short_name +"."+ domainname
            html = comicsite.views.comic_site_to_grand_challenge_html(project,url)
        else:
            html = comicsite.views.comic_site_to_grand_challenge_html(project)

        return html

    def read_grand_challenge_projectlinks(self):
        filename = "challengestats.xls"
        project_name = settings.MAIN_PROJECT_NAME
        filepath = os.path.join(settings.DROPBOX_ROOT, project_name, filename)
        reader = ProjectExcelReader(filepath,'Challenges')
        try:
            projectlinks = reader.get_project_links()
        except IOError as e:

            logger.warning("Could not read any projectlink information from"
                           " '%s' returning empty string. trace: %s " %(filepath,traceback.format_exc()))
            projectlinks = []
        return projectlinks





@register.tag(name="image_url")
def render_image_url(parser, token):
    """ render image based on image title """
    # split_contents() knows not to split quoted strings.
    tag_name, args = token.split_contents()
    imagetitle = args

    try:
        image = UploadModel.objects.get(title=imagetitle)

    except ObjectDoesNotExist as e:

        errormsg = "Error rendering {% " + token.contents + " %}: Could not find any images named '" + imagetitle + "' in database."
        # raise template.TemplateSyntaxError(errormsg)
        return TemplateErrorNode(errormsg)

    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])

    [isImage, errorMessage] = hasImgExtension(str(image.file))
    if not isImage:
        errormsg = "Error rendering {% " + token.contents + " %}:" + errorMessage
        # raise template.TemplateSyntaxError(errormsg)
        return TemplateErrorNode(errormsg)


    return imagePathNode(image)



class imagePathNode(template.Node):
    """ return local path to the given UploadModel
    """

    def __init__(self, image):
        self.image = image

    def render(self, context):
        path = "/static/media/" + str(self.image.file)

        return path


@register.tag(name="registration")
def render_registration_form(parser, token):
    """ Render a registration form for the current site """

    try:
        projects = ComicSite.objects.all()
    except ObjectDoesNotExist as e:
        errormsg = "Error rendering {% " + token.contents + " %}: Could not find any comicSite object.."
        return TemplateErrorNode(errormsg)

    return RegistrationFormNode(projects)



class RegistrationFormNode(template.Node):
    """ return HTML form of registration, which links to main registration
    Currently just links to registration
    """

    def __init__(self, projects):
        self.projects = projects

    def render(self, context):
        sitename = context.page.comicsite.short_name
        pagetitle = context.page.title
        signup_url = reverse('comicsite_signin',args=[context.page.comicsite.short_name]) + "?next=" \
                     + reverse('comicsite.views.page', kwargs={'site_short_name':sitename, 'page_title':pagetitle})
        signuplink = makeHTMLLink(signup_url, "sign in")



        registerlink = makeHTMLLink(reverse('comicsite_signup',args=[context.page.comicsite.short_name]), "register")


        if not context['user'].is_authenticated():
            return "To register for " + sitename + ", you need be logged in to COMIC.\
            please " + signuplink + " or " + registerlink

        else:
            participantsgroup = Group.objects.get(name=context.page.comicsite.participants_group_name())
            if participantsgroup in context['user'].groups.all():
                msg = "You have already registered for " + sitename
            else:
                register_url = reverse('comicsite.views._register', kwargs={'site_short_name':sitename})
                msg = makeHTMLLink(register_url, "Register for " + sitename)
            return msg


class TemplateErrorNode(template.Node):
    """Render error message in place of this template tag. This makes it directly obvious where the error occured
    """
    def __init__(self, errormsg):
        self.msg = HTML_encode_django_chars(errormsg)

    def render(self, context):
        return makeErrorMsgHtml(self.msg)


def HTML_encode_django_chars(string):
    """replace curly braces and percent signs by their html encoded equivolents
    """
    string = string.replace("{", "&#123;")
    string = string.replace("}", "&#125;")
    string = string.replace("%", "&#37;")
    return string

def makeHTMLLink(url, linktext):
    return "<a href=\"" + url + "\">" + linktext + "</a>"

def hasImgExtension(filename):

    allowedextensions = [".jpg", ".jpeg", ".gif", ".png", ".bmp"]
    ext = path.splitext(filename)[1]
    if ext in allowedextensions:
         return [True, ""]
    else:
         return [False, "file \"" + filename + "\" does not look like an image. Allowed extensions: [" + ",".join(allowedextensions) + "]"]


def makeErrorMsgHtml(text):
     errorMsgHTML = "<p><span class=\"pageError\"> " + HTML_encode_django_chars(text) + " </span></p>"
     return errorMsgHTML;


@register.tag(name="project_statistics")
def display_project_statistics(parser, token):
    """ Parser for the project statistics tag.
    """
    return ProjectStatisticsNode()


class ProjectStatisticsNode(template.Node):
    def __init__(self):
        pass

    def render(self, context):
        project_name = context.page.comicsite.short_name

        snippet_header = "<div class='statistics'>"
        snippet_footer = "</div>"

        # Get the users belonging to this project
        perm = Group.objects.get(name='{}_participants'.format(project_name))
        users = User.objects.filter(groups=perm).distinct()
        countries = [u.get_profile().get_country_display() for u in users]
        hist_countries = Counter(countries)
        chart_data = [['Country', '#Participants']]
        for key, val in hist_countries.iteritems():
            chart_data.append([str(key), val])

        snippet_geochart = """
        <script type='text/javascript' src='https://www.google.com/jsapi'></script>
        <script type='text/javascript'>
            google.load('visualization', '1', {{'packages': ['geochart']}});
            google.setOnLoadCallback(drawRegionsMap);
            function drawRegionsMap() {{
                var data = google.visualization.arrayToDataTable(
                {data}
                );
                var options = {{}};
                var chart = new google.visualization.GeoChart(document.getElementById('chart_div'));
                chart.draw(data, options);
            }};
        </script>
        <div id="chart_div" style="width: 100%; height: 170px;"></div>
        """.format(data=chart_data)

        snippet = """
        <h1>Statistics</h1><br>

        <p># of users: {num_users}</p>

        {geochart}

        """.format(num_users=len(users), geochart=snippet_geochart)

        return snippet_header + snippet + snippet_footer