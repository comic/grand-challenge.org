from django.db import models
from django.contrib.sites.models import Site
from django.utils.safestring import mark_safe
 

# Create your models here.
class ComicSite(Site):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    # add requirement to native django 'site' obejct that site name should be unique.
    # because names are used in URLS in COMIC, dublicate sitenames would make trouble.     
    #Site.name.unique = True    
    
    skin = models.CharField(max_length = 225)
    comment = models.CharField(max_length = 1024, default="")
        

class Page(models.Model):
    """ A single editable page containing html and maybe special output plugins """
    
    ComicSite = models.ForeignKey("ComicSite")
    title = models.CharField(max_length = 255)
    html = models.TextField()
    
    def rawHTML(self):
        """Display html of this page as html. This uses the mark_safe django method to allow direct html rendering"""
        #TODO : do checking for scripts and hacks here? 
        return mark_safe(self.html)
    
    class Meta:
        """special class holding meta info for this class"""
        # make sure a single site never has two pages with the same name
        unique_together = (("ComicSite", "title"),)
    
    

