"""
Custom tags to use in templates or code to render file lists etc. 
	
 History 
 03/09/2012    -     Sjoerd    -    Created this file

"""
import pdb
import datetime
from os import path
from django import template
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from profiles.forms import SignupFormExtra

from dataproviders import FileSystemDataProvider
from comicmodels.models import FileSystemDataset,UploadModel #FIXME: abstract Dataset should be imported here, not explicit filesystemdataset. the template tag should not care about the type of dataset.
from comicmodels.models import ComicSite,Page
import comicsite.views



# This is needed to use the @register.tag decorator
register = template.Library()

@register.simple_tag
def metafooterpages():
	""" Get the metafooter pages. """
	html_string = "<div class='text'>COMIC:</div>"
	pages = comicsite.views.getPages('COMIC')
	for p in pages:
		if not p.hidden:
			url = reverse('comicsite.views.comicmain', kwargs={'page_title':p.title})
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
    return FileListNode(format_string[1:-1],filefolder[1:-1])


class FileListNode(template.Node):	
    """ Show list of files in given dir 
    """	
	
    def __init__(self, format_string,filefolder):
        self.format_string = format_string
        self.filefolder = filefolder       
        
        
    def render(self, context):    
        dp = FileSystemDataProvider.FileSystemDataProvider(self.filefolder)
        
        images = dp.getImages()    
        htmlOut = "available files:"+", ".join(images)
        return htmlOut
       
@register.tag(name="dataset")
def render_dataset(parser, token):
    """ Given a challenge and a dataset name, show all files in this dataset as list"""	 
    
    
    usagestr = "Tag usage: {% dataset <datasetname>,<comicsitename> %}. <comicsitename> can be\
     			omitted, defaults to current site"
    
    #check some basic stuff
    try:
    	tag_name, args = token.split_contents()
    except ValueError:   
    	errormsg = "Error rendering {% "+token.contents+" %}: tag requires at least one \
    				argument. "	+ usagestr
    	#raise template.TemplateSyntaxError(errormsg)    	
    	return TemplateErrorNode(errormsg)      
    
    	
    if args.count(",") == 0:
        dataset_title = args
        project_name = ""
    elif args.count(",") == 1 :
        dataset_title,project_name = args.split(",")
    else:
    	errormsg = "Error rendering {% "+token.contents+" %}: found "+str(args.count(",")) +\
    				" comma's, expected at most 1."	+ usagestr    	
    	return TemplateErrorNode(errormsg)	
       
    
    return DatasetNode(dataset_title,project_name)


class DatasetNode(template.Node):	
    """ Show list of linked files for given dataset 
    """
    
    def __init__(self, dataset_title,project_name):
        self.dataset_title = dataset_title
        self.project_name = project_name
        
        
    def make_dataset_error_msg(self,msg):
    	errormsg = "Error rendering DataSet '"+ self.dataset_title +"' for project '"+ self.project_name+"': "+msg
        return makeErrorMsgHtml(errormsg)
        
    def render(self, context):
    	
    	if self.project_name == "":
        	self.project_name = context.page.comicsite.short_name
        
    	try:
        #pdb.set_trace()
        	dataset = FileSystemDataset.objects.get(comicsite__short_name=self.project_name,title=self.dataset_title)        
        
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
        	
        	downloadlink = reverse('filetransfers.views.download_handler_filename', kwargs={'project_name':dataset.comicsite.short_name, 
																						    'dataset_title':dataset.title,
																						    'filename':filename})
        	#<a href="{% url filetransfers.views.download_handler_filename project_name='VESSEL12' dataset_title='vessel12' filename='test.png' %}">test </a>
        	links.append("<li><a href=\""+downloadlink+"\">"+ filename+ " </a></li>")
        	
        description = dataset.description
        htmlOut = description+"<ul class=\"dataset\">"+"".join(links)+"</ul>"
        
        return htmlOut
	      
		


@register.tag(name="all_projects")
def render_all_projects(parser, token):
    """ Render an overview of all projects """
    
    try:    	
        projects = ComicSite.objects.all()
    except ObjectDoesNotExist as e:
    	errormsg = "Error rendering {% "+token.contents+" %}: Could not find any comicSite object.."    	
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
        	html += comicsite.views.comic_site_to_html(project)    	        	        	                
        return html


@register.tag(name="image_url")
def render_image_url(parser, token):
    """ render image based on image title """	    
    # split_contents() knows not to split quoted strings.
    tag_name, args = token.split_contents()
    imagetitle = args
        
    try:
        #pdb.set_trace()        
        image = UploadModel.objects.get(title=imagetitle)        
        
    except ObjectDoesNotExist as e:    	
    	
    	errormsg = "Error rendering {% "+token.contents+" %}: Could not find any images named '"+imagetitle+"' in database."
    	#raise template.TemplateSyntaxError(errormsg)
    	return TemplateErrorNode(errormsg)      
        	
    except ValueError:    	
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    
    [isImage,errorMessage] = hasImgExtension(str(image.file))     
    if not isImage:
    	errormsg = "Error rendering {% "+token.contents+" %}:"+ errorMessage
    	#raise template.TemplateSyntaxError(errormsg)
    	return TemplateErrorNode(errormsg)
    	
		
    return imagePathNode(image)



class imagePathNode(template.Node):	
    """ return local path to the given UploadModel 
    """	
	
    def __init__(self, image):
        self.image = image
                
    def render(self, context):
        path = "/static/media/"+str(self.image.file)
        	        	
        return path


@register.tag(name="registration")
def render_registration_form(parser, token):
    """ Render a registration form for the current site """
    
    try:    	
        projects = ComicSite.objects.all()
    except ObjectDoesNotExist as e:
    	errormsg = "Error rendering {% "+token.contents+" %}: Could not find any comicSite object.."    	
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
    	signup_url = reverse('userena_signin') + "?next=" \
    				 + reverse('comicsite.views.page',kwargs={'site_short_name':sitename,'page_title':pagetitle})
    	signuplink = makeHTMLLink(signup_url,"sign in")
    	registerlink = makeHTMLLink(reverse('userena.views.signup', 
										     kwargs={'signup_form':SignupFormExtra}),"register")
    	
    	
        if not context['user'].is_authenticated():
        	return "To register for "+ sitename +", you need be logged in to COMIC.\
        	please "+ signuplink+ " or " + registerlink
        
        else:
        	register_url = reverse('comicsite.views._register',kwargs={'site_short_name':sitename}) 
        	return makeHTMLLink(register_url,"register for "+ sitename )
        
        



class TemplateErrorNode(template.Node):
	"""Render error message in place of this template tag. This makes it directly obvious where the error occured
	"""
	def __init__(self, errormsg):
		self.msg = errormsg
	
	def render(self,context):
		return makeErrorMsgHtml(self.msg)		
		

def makeHTMLLink(url,linktext):
	return "<a href=\""+url+"\">"+ linktext+ "</a>"

def hasImgExtension(filename):
	
	allowedextensions = [".jpg",".jpeg",".gif",".png",".bmp"]
	ext = path.splitext(filename)[1]
	if ext in allowedextensions:
	     return [True,""]	
	else:
	     return [False,"file \""+ filename +"\" does not look like an image. Allowed extensions: ["+",".join(allowedextensions)+"]"]
	
       
def makeErrorMsgHtml(text):
	 errorMsgHTML = "<p><span class=\"pageError\"> "+text+" </span></p>"
	 return errorMsgHTML;
	 