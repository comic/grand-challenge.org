"""
Custom tags to use in templates or code to render file lists etc. 
	
 History 
 03/09/2012    -     Sjoerd    -    Created this file

"""
import datetime
from django import template
from dataproviders import FileSystemDataProvider

# This is needed to use the @register.tag decorator
register = template.Library()

@register.tag(name="current_time")
def do_current_time(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, format_string = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    if not (format_string[0] == format_string[-1] and format_string[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)
    return CurrentTimeNode(format_string[1:-1])


class CurrentTimeNode(template.Node):	
	
    def __init__(self, format_string):
        self.format_string = format_string
    def render(self, context):
        return datetime.datetime.now().strftime(self.format_string)
       
       
       
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
        tag_name, filefolder = token.split_contents()
        format_string = "\"%Y-%m-%d %I:%M %p\""
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    if not (format_string[0] == format_string[-1] and format_string[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)
    return DatasetNode(format_string[1:-1],filefolder[1:-1])


class DatasetNode(template.Node):	
    """ Show list of files for given dataset 
    """	
	
    def __init__(self, format_string,filefolder):
        self.format_string = format_string
        self.filefolder = filefolder       
        
        
    def render(self, context):    
        dp = FileSystemDataProvider.FileSystemDataProvider(self.filefolder)
        
        images = dp.getImages()    
        htmlOut = "available files:"+", ".join(images)
        return htmlOut

       
       
