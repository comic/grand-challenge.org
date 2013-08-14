
from django.core.urlresolvers import resolve
from django.conf import settings
    
class ProjectMiddleware:
    """ Everything you do on comicframework is related to a project. This
    middleware makes this possible without having to duplicate 'project'
    variables everywhere. 
    
    """
    def process_request(self, request):
        """ Adds current project name to any request.
        
        TODO: Geting current project from the name given to it in urls.py is
        stinky. How to do this so that changing urls will not break this? 
    
        """
                    
        resolution = resolve(request.path)
        if resolution.kwargs.has_key("site_short_name"):
            projectname = resolution.kwargs["site_short_name"]
        elif resolution.kwargs.has_key("project_name"):
            projectname = resolution.kwargs["project_name"]
        else:
            projectname = settings.MAIN_PROJECT_NAME
        
        request.projectname = projectname
        
    
    #def process_response(self, request, response):
        
    #    import pdb
    #    pdb.set_trace()
        
        