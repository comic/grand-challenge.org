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

from dataproviders import FileSystemDataProvider
from comicmodels.models import FileSystemDataset #FIXME: abstract Dataset should be imported here, not explicit filesystemdataset. the template tag should not care about the type of dataset.
from comicsite.models import ComicSite,Page
import comicsite.views


# This is needed to use the @register.tag decorator
register = template.Library()

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
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, args = token.split_contents()
        project_name, dataset_title = args.split(",")
        #pdb.set_trace()        
        dataset = FileSystemDataset.objects.get(comicsite__short_name=project_name,title=dataset_title)        
        filefolder = dataset.get_data_dir()        
        format_string = "\"%Y-%m-%d %I:%M %p\""
    except ObjectDoesNotExist as e:    	
    	
    	errormsg = "Error rendering {% "+token.contents+" %}: Could not find any dataset named '"+dataset_title+"' belonging to project '"+project_name+"' in database."
    	#raise template.TemplateSyntaxError(errormsg)    	
    	return TemplateErrorNode(errormsg)
    	
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    if not (format_string[0] == format_string[-1] and format_string[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)
    return DatasetNode(format_string[1:-1],filefolder,dataset)



class DatasetNode(template.Node):	
    """ Show list of linked files for given dataset 
    """	
	
    def __init__(self, format_string,filefolder,dataset):
        self.format_string = format_string
        self.filefolder = filefolder       
        self.dataset = dataset
        
    def render(self, context):    
        dp = FileSystemDataProvider.FileSystemDataProvider(self.filefolder)
        
        filenames = dp.getAllFileNames()
        links = []
        for filename in filenames:
        	
        	downloadlink = reverse('filetransfers.views.download_handler_filename', kwargs={'project_name':self.dataset.comicsite.short_name, 
																						    'dataset_title':self.dataset.title,
																						    'filename':filename})
        	#<a href="{% url filetransfers.views.download_handler_filename project_name='VESSEL12' dataset_title='vessel12' filename='test.png' %}">test </a>
        	links.append("<li><a href=\""+downloadlink+"\">"+ filename+ " </a></li>")
        	
        description = self.dataset.description
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



class TemplateErrorNode(template.Node):
	"""Render error message in place of this template tag. This makes it directly obvious where the error occured
	"""
	def __init__(self, errormsg):
		self.msg = errormsg
	
	def render(self,context):
		errormsgHTML = "<span class=\"pageError\"> "+self.msg+" </span>"
		return errormsgHTML
       
       
