from django.db import models
from django.contrib.sites.models import Site
from django.utils.safestring import mark_safe
from django.db.models import Max

# Create your models here.
class ComicSite(Site):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    # TODO: Sjoerd - Is it correct to define the params below as class params, or should these be in an init method? 
    
    short_name = models.CharField(max_length = 50, default="", help_text = "short name used in url, specific css, files etc. No spaces allowed")
    skin = models.CharField(max_length = 225)    
        
    comment = models.CharField(max_length = 1024, default="", blank=True)
        

class Page(models.Model):
    """ A single editable page containing html and maybe special output plugins """
    
    order = models.IntegerField(editable=False, default=1, help_text = "Determines order in which pages appear on site")     
    ComicSite = models.ForeignKey("ComicSite")
    
    title = models.CharField(max_length = 255)
    html = models.TextField()
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        
        #when saving for the first time only, put this page last in oder 
        if not self.id:
            # get max value of order for current pages.
            max_order = Page.objects.filter(ComicSite__pk=self.ComicSite.pk).aggregate(Max('order'))                
            self.order = max_order["order__max"] + 1
        
            
    
    def rawHTML(self):
        """Display html of this page as html. This uses the mark_safe django method to allow direct html rendering"""
        #TODO : do checking for scripts and hacks here? 
        return mark_safe(self.html)
    
    def move(self, move):
        if move == 'UP':
            mm = Page.objects.get(ComicSite=self.ComicSite,order=self.order-1)
            mm.order += 1
            mm.save()
            self.order -= 1
            self.save()
        if move == 'DOWN':
            mm = Page.objects.get(ComicSite=self.ComicSite,order=self.order+1)
            mm.order -= 1
            mm.save()
            self.order += 1
            self.save()
        if move == 'FIRST':
            raise NotImplementedError("Somebody should implement this!")
        if move == 'LAST':
            raise NotImplementedError("Somebody should implement this!")
    
    
    class Meta:
        """special class holding meta info for this class"""
        # make sure a single site never has two pages with the same name because page names
        # are used as keys in urls
        unique_together = (("ComicSite", "title"),)
         
        # when getting a list of these objects this ordering is used
        ordering = ['ComicSite','order']
    
    
class ComicSiteException(Exception):
    """ any type of exception for which a django or python exception is not defined """
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)
    
