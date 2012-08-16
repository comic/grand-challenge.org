from django.db import models
from django.contrib.sites.models import Site
from django.utils.safestring import mark_safe
from django.db.models import Max
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist

from guardian.shortcuts import assign

# Create your models here.


class ComicSiteModel(models.Model):
    """An object which can be shown or used in the comicsite framework. This base class should handle common functions
     such as authorization.
    """
    #user = models.ManyToManyField()
    pass


class ComicSite(models.Model):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    short_name = models.CharField(max_length = 50, default="", help_text = "short name used in url, specific css, files etc. No spaces allowed")
    skin = models.CharField(max_length = 225)
    comment = models.CharField(max_length = 1024, default="", blank=True)
    
    def __unicode__(self):
        """ string representation for this object"""
        return self.short_name
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        #TODO check whether short name is really clean and short!
            
    def admin_group_name(self):
        """ returns the name of the admin group which should have all rights to this ComicSite instance"""
        return self.short_name+"_admins"
    
    def participants_group_name(self):
        """ returns the name of the participants group, which should have some rights to this ComicSite instance"""
        return self.short_name+"_participants"
    
    

class Page(models.Model):
    """ A single editable page containing html and maybe special output plugins """
    
    order = models.IntegerField(editable=False, default=1, help_text = "Determines order in which pages appear on site")
    ComicSiteTemp = models.IntegerField(default = 0, help_text = "just a temp var to hold foreign key while rebasing this model from ComicSite model")     
    ComicSite = models.ForeignKey("ComicSite")
    title = models.CharField(max_length = 255)
    html = models.TextField()
    
    def __unicode__(self):
        """ string representation for this object"""
        return "Page '"+self.title+"'";
    
    
    def clean(self):
        """ clean method is called automatically for each save in admin"""
        
        #when saving for the first time only, put this page last in order 
        if not self.id:
            # get max value of order for current pages.
            try:            
                max_order = Page.objects.filter(ComicSite__pk=self.ComicSite.pk).aggregate(Max('order'))                
            except ObjectDoesNotExist :
                max_order = None
                                        
            if max_order["order__max"] == None:
                self.order = 1
            else:
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
    
    
