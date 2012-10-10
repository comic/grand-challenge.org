"""
 Custom processors to pass variables to views rendering template tags 
 see http://www.djangobook.com/en/2.0/chapter09.html  
"""

from django.template import RequestContext


class ComicSiteRequestContext(RequestContext):
    """ RequestContext with added comicsite. Could not get comicsite from httprequest so
        passing it in init()"""
    # I want to add comicsite instance to current context so that template tags know
    # which comicsite is rendering them. You can add a custom context processor to 
    # requestContext but this can only return variables based on the given httpcontext
    # This does not contain any info on which comicsite is rendering, so I chose to add
    # comicsite param to init.
        
    def __init__(self,request,comicsite,*args,**kwargs):
        super(ComicSiteRequestContext, self).__init__(request,*args,**kwargs)
        self.comicsite = comicsite
        
    
    
class test():
    test = "yes"