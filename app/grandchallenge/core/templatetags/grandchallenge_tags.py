import logging
import ntpath
import os
import random
import re
import string
import traceback
from io import StringIO
from urllib.parse import urljoin

from django import template
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import DefaultStorage
from django.db.models import Count
from django.template import defaulttags
from django.urls import reverse as reverse_djangocore
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from matplotlib.backends.backend_svg import FigureCanvasSVG as FigureCanvas
from matplotlib.figure import Figure

import grandchallenge.core.views
from grandchallenge.core.api import get_public_results_by_challenge_name
from grandchallenge.core.exceptions import PathResolutionException
from grandchallenge.core.templatetags import library_plus
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.utils.HtmlLinkReplacer import HtmlLinkReplacer
from grandchallenge.profiles.models import UserProfile

register = library_plus.LibraryPlus()
logger = logging.getLogger("django")


def parseKeyValueToken(token):
    """Parses token content string into a parameter dictionary
    
    Args:        
        token (django.base.Token): Object representing the string content of
            the template tag. Key values are expected to be of the format         
            key1:value1 key2:value2,...

    Returns:
        A dictionary of key:value pairs
        
    Raises:
        ValueError: if token contents are not in key:val1 key:val2 .. format
        
    """
    split = token.split_contents()
    tag = split[0]
    args = split[1:]
    if "=" in "".join(args):
        raise ValueError(
            "Please use colon ':' instead of equals '=' to separate keys and values"
        )

    return dict([param.split(":") for param in args])


def get_usagestr(function_name):
    """
    Return usage string for a registered template tag function. For displaying
    this info in errors or tag overviews
    """
    if function_name in register.usagestrings:
        usagestr = register.usagestrings[function_name]
    else:
        usagestr = ""
    return sanitize_django_items(usagestr)


@register.tag(
    name="taglist",
    usagestr="""
              <% taglist %> :
              show all available tags
                       """,
)
def get_taglist(parser, token):
    return TagListNode()


def subdomain_is_projectname():
    """ Check whether this setting is true in settings. Return false if not found

    """
    is_projectname = False
    if hasattr(settings, "SUBDOMAIN_IS_PROJECTNAME"):
        is_projectname = settings.SUBDOMAIN_IS_PROJECTNAME
        if is_projectname and not hasattr(settings, "MAIN_HOST_NAME"):
            msg = """Key 'SUBDOMAIN_IS_PROJECTNAME' was defined in settings,
             but 'MAIN_HOST_NAME' was not. These belong together. Please
             add 'MAIN_HOST_NAME' and set it to the hostname of your site."""
            raise ImproperlyConfigured(msg)

    return is_projectname


@register.tag
def url(parser, token):
    """Overwrites built in url tag to use . It works identicaly, except that where possible
    it will use subdomains to refer to a project instead of a full url path.

    For example, if the subdomain is vessel12.domain.com it will refer to a page
    'details' as /details/ instead of /site/vessel12/details/

    REQUIREMENTS:
    * MIDDLEWARE_CLASSES in settings should contain
      'core.middleware.subdomain.SubdomainMiddleware'

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
    orgnode = defaulttags.url(parser, token)
    return comic_URLNode(
        orgnode.view_name, orgnode.args, orgnode.kwargs, orgnode.asvar
    )


def filter_by_extension(filenames, extensions):
    """Takes two lists of strings. Return only strings that end with any of 
    the strings in extensions. 
    
    """
    filtered = []
    for extension in extensions:
        filtered = filtered + [f for f in filenames if f.endswith(extension)]
    return filtered


def resolve_path(path, parser, context):
    """Try to resolve all parameters in path   
    
    Paths in COMIC template tag parameters can include variables. Try to
    resolve these and throw error if this is not possible. 
    path can be of three types:
        * a raw filename like "stuff.html" or "results/table1.txt"
        * a filname containing a variable like "results/{{teamid}}/table1.txt"
        * a django template variable like "site.short_name"
    
    Args:
        Path (string)
        parser (django object) 
        context (django context given tag render function)
        
        
    Returns:
        resolved path (string)
    
    Raises:
        PathResolutionException when path cannot be resolved
        :param path: 
                
    """
    # Find out what type it is:
    # If it contains any / or {{ resolving as django var
    # is going to throw an error. Prevent unneeded exception, just skip
    # rendering as var in that case.
    path_resolved = ""
    if not in_list(["{", "}", "\\", "/"], path):
        compiled_filter = parser.compile_filter(strip_quotes(path))
        path_resolved = compiled_filter.resolve(context)
    # if resolved filename is empty, resolution failed, just treat this
    # param as a filepath
    if path_resolved == "":
        filename = strip_quotes(path)
    else:
        filename = path_resolved
    # if there are {{}}'s in there, try to substitute this with url
    # parameter given in the url
    filename = substitute(filename, context["request"].GET.items())
    # If any {{parameters}} are still in filename they were not replaced.
    # This filename is missing information, show this as error text.
    if re.search(r"{{\w+}}", str(filename)):
        missed_parameters = re.findall(r"{{\w+}}", str(filename))
        found_parameters = context["request"].GET.items()
        if not found_parameters:
            found_parameters = "None"
        error_msg = (
            "I am missing required url parameter(s) %s, url parameter(s) found: %s "
            "" % (missed_parameters, found_parameters)
        )
        raise PathResolutionException(error_msg)

    return filename


def substitute(string, substitutions):
    """
    Take each key in the substitutions dict. See if this key exists
    between double curly braces in string. If so replace with value.

    Example:
    substitute("my name is {{name}}.",{version:1,name=John})
    > "my name is John"
    """
    for key, value in substitutions:
        string = re.sub(re.escape("{{" + key + "}}"), value, string)
    return string


class comic_URLNode(defaulttags.URLNode):
    def render(self, context):
        # get the url the default django method would give.
        url = super().render(context)

        if subdomain_is_projectname() and (
            (
                self.view_name.var
                in ["challenge-homepage", "project_serve_file"]
            )
            or (
                self.view_name.var.split(":")[0]
                in [
                    "evaluation",
                    "teams",
                    "pages",
                    "participants",
                    "admins",
                    "uploads",
                    "datasets",
                ]
            )
        ):
            # Interpret subdomain as a challenge. What would normally be the
            # path to this challenge?
            args = [arg.resolve(context) for arg in self.args]
            kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}

            try:
                project = args[0]
            except IndexError:
                # No project was set, so must be part of the main site
                project = kwargs.get(
                    "challenge_short_name", settings.MAIN_PROJECT_NAME
                )

            if project == settings.MAIN_PROJECT_NAME:
                # this url cannot use the domain name shortcut, so it is
                # probably meant as a link the main comicframework site.
                # in that case hardcode the domain to make sure the sub-
                # domain is gone after following this link
                return settings.MAIN_HOST_NAME + url

            else:
                path_to_site = reverse_djangocore(
                    "challenge-homepage", args=[project]
                )

                if url.startswith(path_to_site):
                    url = url.replace(path_to_site, "/")

                scheme_subsite_and_host = reverse(
                    "challenge-homepage", args=[project]
                )

                return urljoin(scheme_subsite_and_host, url)

        return url


class TagListNode(template.Node):
    """ Print available tags as text
    """

    def __init__(self):
        pass

    def render(self, context):
        html_out = '<table class ="comictable taglist">'
        html_out = html_out + "<tr><th>tagname</th><th>description</th></tr>"
        rowclass = "odd"
        for key, val in register.usagestrings.items():
            if not val == "":
                html_out = (
                    html_out
                    + '<tr class="%s"><td>%s</td><td>%s</td></tr>\
                        '
                    % (rowclass, key, sanitize_django_items(val))
                )
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
    out = out.replace("{{", "&#123;&#123;")
    out = out.replace("}}", "&#125;&#125;")
    out = out.replace("{%", "&#123;&#37;")
    out = out.replace("%}", "&#37;&#125;")
    out = out.replace(">", "&#62;")
    out = out.replace("<", "&#60;")
    out = out.replace("\n", "<br/>")
    return out


@register.simple_tag
def metafooterpages():
    """ Get html for links to general pages like 'contact' """
    html_string = mark_safe("")
    pages = grandchallenge.core.views.getPages(settings.MAIN_PROJECT_NAME)
    for p in pages:
        if not p.hidden:
            url = reverse("mainproject-home", kwargs={"page_title": p.title})
            if subdomain_is_projectname():
                url = settings.MAIN_HOST_NAME + url
            # TODO: JM add class=active to the active link
            # See https://getbootstrap.com/docs/3.3/components/#navbar
            html_string += format_html(
                "<li><a class='metaFooterMenuItem' href='{}'>{}</a></li>",
                url,
                p.display_title if p.display_title else p.title,
            )
    return html_string


@register.simple_tag
def main_page_url():
    """ Gets the url to the main page """
    if settings.SUBDOMAIN_IS_PROJECTNAME:
        return settings.MAIN_HOST_NAME

    else:
        return "/"


@register.tag(
    name="listdir",
    usagestr="""Tag usage: {% listdir <path>:string  <extensionFilter>:ext1,ext2,ext3 %}

              path: directory relative to this projects dropbox folder to list files from. Do not use leading slash.
              extensionFilter: An include filter to specify the file types which should be displayd in the filebrowser.
              """,
)
def listdir(parser, token):
    """ show all files in dir as a downloadable list"""
    usagestr = get_usagestr("listdir")
    try:
        args = parseKeyValueToken(token)
    except ValueError:
        errormsg = (
            "Error rendering {% "
            + token.contents
            + " %}: Error parsing token. "
            + usagestr
        )
        return TemplateErrorNode(errormsg)

    if "path" not in args.keys():
        errormsg = (
            "Error rendering {% "
            + token.contents
            + " %}: 'path' argument is missing."
            + usagestr
        )
        return TemplateErrorNode(errormsg)

    return ListDirNode(args)


class ListDirNode(template.Node):
    """ Show list of linked files for given directory
    """

    usagestr = get_usagestr("listdir")

    def __init__(self, args):
        self.path = args["path"]
        self.args = args

    def make_dataset_error_msg(self, msg):
        logger.error("Error listing folder '" + self.path + "': " + msg)
        errormsg = "Error listing folder"
        return makeErrorMsgHtml(errormsg)

    def render(self, context):
        challenge_short_name = context.page.challenge.short_name
        projectpath = challenge_short_name + "/" + self.path
        storage = DefaultStorage()
        try:
            filenames = storage.listdir(projectpath)[1]
        except OSError as e:
            return self.make_dataset_error_msg(str(e))

        filenames.sort()
        # if extensionsFilter is given,  show only filenames with those extensions
        if "extensionFilter" in self.args.keys():
            extensions = self.args["extensionFilter"].split(",")
            filenames = filter_by_extension(filenames, extensions)
        links = []
        for filename in filenames:
            downloadlink = reverse(
                "serving:challenge-file",
                kwargs={
                    "challenge_short_name": challenge_short_name,
                    "path": f"{self.path}/{filename}",
                },
            )
            links.append(
                '<li><a href="' + downloadlink + '">' + filename + " </a></li>"
            )
        htmlOut = '<ul class="dataset">' + "".join(links) + "</ul>"
        return htmlOut


@register.tag(name="image_browser")
def render_image_browser(parser, token):
    """Given a folder and project, render a browser so you can skip through them in browser
    
    """
    usagestr = """Tag usage: {% image_browser path:string - path relative to current project
                                              config:string - path relative to current project %}
                  """
    try:
        args = parseKeyValueToken(token)
    except ValueError:
        errormsg = (
            "Error rendering {% "
            + token.contents
            + " %}: Error parsing token. "
            + usagestr
        )
        return TemplateErrorNode(errormsg)

    if "path" not in args.keys():
        errormsg = (
            "Error rendering {% "
            + token.contents
            + " %}: path argument is missing."
            + usagestr
        )
        return TemplateErrorNode(errormsg)

    return ImageBrowserNode(args, parser)


class ImageBrowserNode(template.Node):
    """Render jquery browser to go through all images in given folder
    
    """

    def __init__(self, args, parser):
        self.args = args
        self.parser = parser

    def make_dataset_error_msg(self, msg):
        logger.error(
            "Error rendering Visualization '" + str(self.args) + ":" + msg
        )
        errormsg = "Error rendering Visualization"
        return makeErrorMsgHtml(errormsg)

    def render(self, context):
        import json

        # Get variables used in rendering html below.
        # path can contain variables like "/results/{{resultId}}/screenshots/"
        path_resolved = resolve_path(self.args["path"], self.parser, context)
        try:
            filenames = self.get_filenames(context, path_resolved)
        except OSError as e:
            return self.make_dataset_error_msg(str(e))

        try:
            public_results = get_public_results_by_challenge_name(
                context["site"].short_name
            )
        except OSError as e:
            # if no results can be found just skip it
            public_results = []
        # Url relative to hostname. To serve /foo/file.txt from project datafolder,
        # what url needs to go in front?  Thsi var can be used in javascript to
        # create links. Using dummyfile because django resolution does not except
        # explicit empty strings.
        serve_file_prefix = reverse(
            "project_serve_file",
            kwargs={
                "challenge_short_name": context["site"].short_name,
                "path": "dummyfile",
            },
        )
        # remove "dummyfile/" from end of path again. This feels dirty but I cannot see
        # much wrong with it here.
        serve_file_prefix = serve_file_prefix[:-10]
        htmlOut = """
          <h3>Results viewer</h3>
            <div id="resultViewer">
                <div id="resultViewerGUI"></div>
                <div id="resultMessage"></div>
            </div>
            <div style="clear:both;"></div>
        
        <script type="text/javascript" src="{main_hostname}/static/js/challengeResultViewer/challengeResultViewer.js"></script>
        <script type="text/javascript">
            // some useful vars you might need to build a browser in javascript
            var project_info = {project_info};            
        </script> 
        {custom_options_include} 
        <script type="text/javascript">            
            //combine default options generated by django with user-defined options
            var django_generated_options = {dg_options};
            var user_defined_options = options;
            options = $.extend({{}},user_defined_options,django_generated_options);
            viewer{viewer_id} = new ResultViewerGUI();
            viewer{viewer_id}.init("#resultViewerGUI",options);
            viewer{viewer_id}.loadAllScreenshots();
        </script> 

        """.format(
            main_hostname=settings.MAIN_HOST_NAME,
            path=path_resolved,
            viewer_id=random.randrange(100000, 999999),
            # just 6 random numbers
            custom_options_include=self.get_custom_options_include(context),
            project_info=json.dumps(
                {
                    "public_results": public_results,
                    "url_params": self.get_url_params(context),
                }
            ),
            dg_options=json.dumps(
                {
                    "dirs": [path_resolved],
                    "fileNames": filenames,
                    "serve_file_prefix": serve_file_prefix,
                }
            ),
        )
        return htmlOut

    def get_custom_options_include(self, context):
        """ The viewer options and behaviour can be custimized by passing along a piece of 
        javascript."""
        challenge_short_name = context.page.challenge.short_name
        if "config" in self.args:
            downloadlink = reverse(
                "project_serve_file",
                kwargs={
                    "challenge_short_name": challenge_short_name,
                    "path": self.args["config"],
                },
            )
            return """<script type="text/javascript" src="{}"></script>""".format(
                downloadlink
            )

        else:
            return "<script> options = undefined; </script>"

    def get_url_params(self, context):
        url_params = context["request"].GET.items()
        params = {}
        # convert tuples to dictionary because this is easier to read
        for (key, value) in url_params:
            params[key] = value
        return params

    def get_filenames(self, context, path):
        """ Get all filenames in path
        
        Raises OSError if directory can not be found
        """
        challenge_short_name = context.page.challenge.short_name
        projectpath = challenge_short_name + "/" + path
        storage = DefaultStorage()
        filenames = storage.listdir(projectpath)[1]
        filenames.sort()
        # if extensionsFilter is given,  show only filenames with those extensions
        if "extensionFilter" in self.args.keys():
            extensions = self.args["extensionFilter"].split(",")
            filenames = filter_by_extension(filenames, extensions)
        return filenames


def add_quotes(s: str = ""):
    """ add quotes to string if not there
    """
    s = strip_quotes(s)
    return "'" + s + "'"


def strip_quotes(s: str = ""):
    """ strip outermost quotes from string if there
    """
    if len(s) >= 2 and (s[0] == s[-1]) and s[0] in ("'", '"'):
        return s[1:-1]

    return s


def in_list(needles, haystack):
    """ return True if any of the strings in string array needles is in haystack

    """
    for needle in needles:
        if needle in haystack:
            return True

    return False


@register.tag(
    name="get_project_prefix",
    usagestr="""Tag usage: {% get_api_prefix %}
                  Get the base url for this project as string, with trailing slash
                  """,
)
def get_project_prefix(parser, token):
    """Get the base url for this project as string, with trailing slash.
    Created this originally to be able to use for project-specific api calls in
    javascript"""
    return RenderGetProjectPrefixNode()


class RenderGetProjectPrefixNode(template.Node):
    usagestr = get_usagestr("get_project_prefix")

    def render(self, context):
        try:
            projectname = context["site"].short_name
        except (AttributeError, KeyError):
            projectname = settings.MAIN_PROJECT_NAME
        url = reverse("challenge-homepage", args=[projectname])
        return url


@register.tag(name="insert_file")
def insert_file(parser, token):
    """Render the contents of a file from the local dropbox folder of the 
    current project
        
    """
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
        args["file"] = add_quotes(filename)
    replacer = HtmlLinkReplacer()
    return InsertFileNode(args, replacer, parser)


class InsertFileNode(template.Node):
    def __init__(self, args, replacer, parser):
        self.args = args
        self.replacer = replacer
        self.parser = parser

    def make_error_msg(self, msg):
        logger.error(
            "Error including file '" + "," + self.args["file"] + "': " + msg
        )
        errormsg = "Error including file"
        return makeErrorMsgHtml(errormsg)

    def is_inside_project_data_folder(self, folder, project):
        """ For making sure nosey people do not use too many ../../../ in paths
        to snoop around in the filesystem.
        
        folder: string containing a filepath
        project: a comicsite object
        """
        data_folder = project.get_project_data_folder()
        folder = self.make_canonical_path(folder)
        data_folder = self.make_canonical_path(data_folder)
        if folder.startswith(data_folder):
            return True

        else:
            return False

    def make_canonical_path(self, path):
        """ Make this a nice path, with / separators
        
        """
        path = path.replace("\\\\", "/")
        return path.replace("\\", "/")

    def replace_links(self, filename, contents, currentpage):
        """Relative urls which work on disk might not
        work properly when used in included file. Make sure any links in contents
        still point to the right place 
        
        """
        # any relative link inside included file has to be replaced to make it work within the COMIC
        # context.
        base_url = reverse(
            "pages:insert-detail",
            kwargs={
                "challenge_short_name": currentpage.challenge.short_name,
                "page_title": currentpage.title,
                "dropboxpath": "remove",
            },
        )
        # for some reason reverse matching does not work for emtpy dropboxpath (maybe views.dropboxpage
        # throws an error?. Workaround is to add 'remove' as path and chop this off the returned link.
        # nice.
        base_url = base_url[:-7]  # remove "remove/" from baseURL
        current_path = (
            ntpath.dirname(filename) + "/"
        )  # path of currently inserted file
        replaced = self.replacer.replace_links(
            contents, base_url, current_path
        )
        html_out = replaced
        return html_out

    def render(self, context):
        # text typed in the tag
        token = self.args["file"]
        try:
            filename = resolve_path(token, self.parser, context)
        except PathResolutionException as e:
            return self.make_error_msg(f"Path Resolution failed: {e}")

        challenge_short_name = context["site"].short_name
        filepath = os.path.join(
            settings.MEDIA_ROOT, challenge_short_name, filename
        )
        filepath = os.path.abspath(filepath)
        filepath = self.make_canonical_path(filepath)
        # when all rendering is done, check if the final path is still not getting
        # into places it should not go.
        if not self.is_inside_project_data_folder(filepath, context["site"]):
            error_msg = "'{}' cannot be opened because it is outside the current project.".format(
                filepath
            )
            return self.make_error_msg(error_msg)

        storage = DefaultStorage()

        try:
            with storage.open(filepath, "r") as f:
                contents = f.read()
        except Exception as e:
            return self.make_error_msg("error opening file:" + str(e))

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
        if "currentpage" in context:
            currentpage = context["currentpage"]
        elif hasattr(context, "page"):
            currentpage = context.page
        else:
            currentpage = None

        if currentpage and os.path.splitext(filename)[1] != ".css":
            html_out = self.replace_links(
                filename, contents, currentpage
            ).decode()
        # rewrite relative links
        else:
            html_out = contents

        return html_out


@register.tag(name="insert_graph")
def insert_graph(parser, token):
    """ Render a csv file from the local dropbox to a graph """
    usagestr = """Tag usage: {% insert_graph <file> type:<type>%}
                  <file>: filepath relative to project dropboxfolder.
                  <type>: how should the file be parsed and rendered?
                  Example: {% insert_graph results/test.txt %}
                  You can use url parameters in <file> by using {{curly braces}}.
                  Example: {% inster_graphfile {{id}}/result.txt %} called with ?id=1234
                  appended to the url will show the contents of "1234/result.txt".
                  """
    split = token.split_contents()
    tag = split[0]
    all_args = split[1:]
    if len(all_args) > 2:
        error_message = "Expected no more than 2 arguments, found " + str(
            len(all_args)
        )
        return TemplateErrorNode(error_message + "usage: \n" + usagestr)

    else:
        args = {"file": all_args[0]}
        if len(all_args) == 2:
            args["type"] = all_args[1].split(":")[1]
        else:
            args["type"] = "anode09"  # default
    replacer = HtmlLinkReplacer()
    return InsertGraphNode(args, replacer)


class InsertGraphNode(template.Node):
    def __init__(self, args, replacer):
        self.args = args
        self.replacer = replacer

    def make_error_msg(self, msg):
        logger.error(
            "Error rendering graph from file '"
            + ","
            + self.args["file"]
            + "': "
            + msg
        )
        errormsg = "Error rendering graph from file"
        return makeErrorMsgHtml(errormsg)

    def render(self, context):
        filename_raw = self.args["file"]
        filename_clean = substitute(
            filename_raw, context["request"].GET.items()
        )
        # If any url parameters are still in filename they were not replaced. This filename
        # is missing information..
        if re.search(r"{{\w+}}", filename_clean):
            missed_parameters = re.findall(r"{{\w+}}", filename_clean)
            found_parameters = context["request"].GET.items()
            if not found_parameters:
                found_parameters = "None"
            error_msg = (
                "I am missing required url parameter(s) %s, url parameter(s) found: %s "
                "" % (missed_parameters, found_parameters)
            )
            return self.make_error_msg(error_msg)

        challenge_short_name = context.page.challenge.short_name
        filename = os.path.join(
            settings.MEDIA_ROOT, challenge_short_name, filename_clean
        )
        storage = DefaultStorage()
        try:
            contents = storage.open(filename, "r").read()
        except Exception as e:
            return self.make_error_msg(str(e))

        # TODO check content safety
        # any relative link inside included file has to be replaced to make it work within the COMIC
        # context.
        base_url = reverse(
            "pages:insert-detail",
            kwargs={
                "challenge_short_name": context.page.challenge.short_name,
                "page_title": context.page.title,
                "dropboxpath": "remove",
            },
        )
        # for some reason reverse matching does not work for emtpy dropboxpath (maybe views.dropboxpage
        # throws an error?. Workaround is to add 'remove' as path and chop this off the returned link
        # nice.
        base_url = base_url[:-7]  # remove "remove/" from baseURL
        current_path = (
            ntpath.dirname(filename_clean) + "/"
        )  # path of currently inserted file
        try:
            render_function = getrenderer(self.args["type"])
        # (table,headers) = read_function(filename)
        except Exception as e:
            return self.make_error_msg("getrenderer: %s" % e)

        RENDER_FRIENDLY_ERRORS = True
        # FRIENDLY = on template tag error, replace template tag with red error
        #            text
        # NOT SO FRIENDLY = on template tag error, stop rendering, show full
        #                   debug page
        try:
            svg_data = render_function(filename)
        except Exception as e:
            if RENDER_FRIENDLY_ERRORS:
                return self.make_error_msg(
                    str(
                        "Error in render funtion '%s()' : %s"
                        % (render_function.__name__, traceback.format_exc(0))
                    )
                )

            else:
                raise

        # self.get_graph_svg(table,headers)
        # html_out = "A graph rendered! source: '%s' <br/><br/> %s" %(filename_clean,svg_data)
        html_out = svg_data
        # rewrite relative links
        return html_out


def getrenderer(renderer_format):
    """Holds list of functions which can take in a filepath and return html to show a graph.
    By using this function we can easily list all available renderers and provide some safety:
    only functions listed here can be called from the template tag render_graph.
    """
    renderers = {
        "anode09": render_anode09_result,
        "anode09_table": render_anode09_table,
    }
    if renderer_format not in renderers:
        raise Exception(
            "reader for format '%s' not found. Available formats: %s"
            % (renderer_format, ",".join(renderers.keys()))
        )

    return renderers[renderer_format]


def canvas_to_svg(canvas):
    """ Render matplotlib canvas as string containing html/svg instructions. These instructions can be
    pasted into any html page and will be rendered as graph by any modern browser.

    """
    imgdata = StringIO()
    imgdata.seek(0, os.SEEK_END)
    canvas.print_svg(imgdata, format="svg")
    svg_data = imgdata.getvalue()
    imgdata.close()
    return svg_data


def render_anode09_result(filename):
    """ Read in a file with the anode09 result format, return html to render an 
        FROC graph.
        To be able to read this without changing the evaluation
        executable. anode09 results have the following format:

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
    variables = parse_php_arrays(filename)
    assert variables != {}, (
        "parsed result of '%s' was emtpy. I cannot plot anything" % filename
    )
    fig = Figure(facecolor="white")
    canvas = FigureCanvas(fig)
    classes = {
        "small": "nodules < 5mm",
        "large": "nodules > 5mm",
        "isolated": "isolated nodules",
        "vascular": "vascular nodules",
        "pleural": "pleural nodules",
        "fissure": "peri-fissural nodules",
        "froc": "all nodules",
    }
    for key, label in classes.items():
        fig.gca().plot(
            variables["x"], variables[key + "y"], label=label, gid=key
        )
    fig.gca().set_xlim([10 ** -2, 10 ** 2])
    fig.gca().set_ylim([0, 1])
    fig.gca().legend(loc="best", prop={"size": 10})
    fig.gca().grid()
    fig.gca().grid(which="minor")
    fig.gca().set_xlabel("Average FPs per scan")
    fig.gca().set_ylabel("Sensitivity")
    fig.gca().set_xscale("log")
    fig.set_size_inches(8, 6)
    return canvas_to_svg(canvas)


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
    variables = parse_php_arrays(filename)
    assert variables != {}, (
        "parsed result of '%s' was emtpy. I cannot create table" % filename
    )
    table_id = id_generator()
    tableHTML = (
        """<table border=1 class = "comictable csvtable sortable" id="%s">
            <thead><tr>
                <td class ="firstcol">FPs/scan</td><td align=center width='54'>1/8</td>
                <td align=center width='54'>1/4</td>
                <td align=center width='54'>1/2</td><td align=center width='54'>1</td>
                <td align=center width='54'>2</td><td align=center width='54'>4</td>
                <td align=center width='54'>8</td><td align=center width='54'>average</td>
            </tr></thead>"""
        % table_id
    )
    tableHTML = tableHTML + "<tbody>"
    tableHTML = tableHTML + array_to_table_row(
        ["small nodules"] + variables["smallscore"]
    )
    tableHTML = tableHTML + array_to_table_row(
        ["large nodules"] + variables["largescore"]
    )
    tableHTML = tableHTML + array_to_table_row(
        ["isolated nodules"] + variables["isolatedscore"]
    )
    tableHTML = tableHTML + array_to_table_row(
        ["vascular nodules"] + variables["vascularscore"]
    )
    tableHTML = tableHTML + array_to_table_row(
        ["pleural nodules"] + variables["pleuralscore"]
    )
    tableHTML = tableHTML + array_to_table_row(
        ["peri-fissural nodules"] + variables["fissurescore"]
    )
    tableHTML = tableHTML + array_to_table_row(
        ["all nodules"] + variables["frocscore"]
    )
    tableHTML = tableHTML + "</tbody>"
    tableHTML = tableHTML + "</table>"
    return '<div class="comictablecontainer">' + tableHTML + "</div>"


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """ thanks to Ignacio Vazquez-Abrams on stackoverflow"""
    return "".join(random.choice(chars) for x in range(size))


def array_to_table_row(rowvalues, trclass=""):
    output = '<tr class = "%s">' % trclass
    for value in rowvalues:
        if type(value) is float:
            output = output + "<td>%.3f</td>" % value
        else:
            output = output + "<td>%s</td>" % str(value)
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
    with storage.open(filename, "r") as f:
        content = f.read()
        content = content.replace("\n", "")
        php = re.compile(r"\<\?php(.*?)\?\>", re.DOTALL)
        s = php.search(content)
        assert s is not None, (
            "trying to parse a php array, but could not find anything like &lt;? php /?&gt; in '%s'"
            % filename
        )
        phpcontent = s.group(1)
        phpvars = phpcontent.split("$")
        phpvars = [x for x in phpvars if x != ""]  # remove empty
        if verbose:
            print("found %d php variables in %s. " % (len(phpvars), filename))
            print("parsing %s into int arrays.. " % filename)
        # check whether this looks like a php var
        phpvar = re.compile(
            r"([a-zA-Z]+[a-zA-Z0-9]*?)=array\((.*?)\);", re.DOTALL
        )
        for var in phpvars:
            result = phpvar.search(var)
            # TODO Log these messages as info
            if result is None:
                msg = (
                    "Could not match regex pattern '%s' to '%s'\
                                        "
                    % (phpvar.pattern, var)
                )
                continue

            if len(result.groups()) != 2:
                msg = (
                    "Expected to find  varname and content,\
                          but regex '%s' found %d items:%s "
                    % (
                        phpvar.pattern,
                        len(result.groups()),
                        "[" + ",".join(result.groups()) + "]",
                    )
                )
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
        args = {"url_parameter": all_args[0]}
    args["token"] = token
    return UrlParameterNode(args)


class UrlParameterNode(template.Node):
    def __init__(self, args):
        self.args = args

    def make_error_msg(self, msg):
        logger.error(
            "Error in url_parameter tag: '" + ",".join(self.args) + "': " + msg
        )
        errormsg = "Error in url_parameter tag"
        return makeErrorMsgHtml(errormsg)

    def render(self, context):
        if self.args["url_parameter"] in context["request"].GET:
            return context["request"].GET[self.args["url_parameter"]]

        else:
            logger.error(
                "Error rendering %s: Parameter '%s' not found in request URL"
                % (
                    "{%  " + self.args["token"].contents + "%}",
                    self.args["url_parameter"],
                )
            )
            error_message = "Error rendering"
            return makeErrorMsgHtml(error_message)


class TemplateErrorNode(template.Node):
    """Render error message in place of this template tag. This makes it directly obvious where the error occured
    """

    def __init__(self, errormsg):
        self.msg = HTML_encode_django_chars(errormsg)

    def render(self, context):
        return makeErrorMsgHtml(self.msg)


def HTML_encode_django_chars(string):
    """replace curly braces and percent signs by their html encoded equivalents
    """
    string = string.replace("{", "&#123;")
    string = string.replace("}", "&#125;")
    string = string.replace("%", "&#37;")
    return string


def makeErrorMsgHtml(text):
    errorMsgHTML = (
        '<p><span class="pageError"> '
        + HTML_encode_django_chars(text)
        + " </span></p>"
    )
    return errorMsgHTML


@register.tag(name="project_statistics")
def display_project_statistics(parser, token):
    usagestr = """Tag usage: {% project_statistics %}
                  Displays a javascript map of the world listing the country
                  of residence entered by each participants for this project when they signed up.
                  
                  """
    return ProjectStatisticsNode()


@register.tag(name="allusers_statistics")
def display_project_statistics(parser, token):
    usagestr = """Tag usage: {% allusers_statistics %}
                  Displays a javascript map of the world which listing the country
                  of residence entered by each user of the framework when they signed up.
                  """
    try:
        _, include_header = token.split_contents()
        if include_header.lower() == "false":
            include_header = False
    except ValueError:
        include_header = True
    return ProjectStatisticsNode(allusers=True, include_header=include_header)


class ProjectStatisticsNode(template.Node):
    def __init__(self, allusers=False, include_header=True):
        """
        Allusers is meant to be used on the main website, and does not filter for
        current project, but shows all registered users in the whole system
        """
        self.allusers = allusers
        self.include_header = include_header

    def render(self, context):
        """
        Renders a map of users and statistics for the current project. This is slow, so cache the response for 10 mins.
        :param context: the page context
        :return: the map html string
        """

        all_users = self.allusers
        key = "ProjectStatisticsNode.{}.{}".format(
            context.page.challenge.pk, all_users
        )
        content = cache.get(key)
        if content is None:
            content = self._get_map(
                context.page.challenge, all_users, self.include_header
            )
            cache.set(key, content, 10 * 60)
        return content

    @classmethod
    def _get_map(cls, challenge, all_users, include_header):
        snippet_header = "<div class='statistics'>"
        snippet_footer = "</div>"

        if all_users:
            User = get_user_model()
            users = User.objects.all().distinct()
        else:
            users = challenge.get_participants()

        country_counts = (
            UserProfile.objects.filter(user__in=users)
            .values("country")
            .annotate(dcount=Count("country"))
        )
        chart_data = [["Country", "#Participants"]]
        for country_count in country_counts:
            chart_data.append(
                [str(country_count["country"]), country_count["dcount"]]
            )
        snippet_geochart = """
        <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
        <script type='text/javascript'>
            google.charts.load('current', {{'packages': ['geochart']}});
            google.charts.setOnLoadCallback(drawRegionsMap);
            function drawRegionsMap() {{
                google.visualization.mapsApiKey = '{maps_api_key}'
                var data = google.visualization.arrayToDataTable(
                {data}
                );
                var options = {{}};
                var chart = new google.visualization.GeoChart(document.getElementById('chart_div'));
                chart.draw(data, options);
            }};
        </script>
        <div id="chart_div"></div>
        """.format(
            data=chart_data, maps_api_key=settings.GOOGLE_MAPS_API_KEY
        )
        snippet = ""
        if include_header:
            snippet += "<h1>Statistics</h1><br/>\n"
        snippet += """
        <p>Number of users: {num_users}</p>
        {geochart}
        """.format(
            num_users=len(users), geochart=snippet_geochart
        )
        return snippet_header + snippet + snippet_footer
