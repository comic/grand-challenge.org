from django.db import models
from django.contrib.sites.models import Site

# Create your models here.
class ComicSite(Site):
    """ A collection of HTML pages using a certain skin. Pages can be browsed and edited."""
    
    
    skin = models.CharField(max_length = 225)


class Page(models.Model):
    """ A single editable page containing html and maybe special output plugins """
    
    ComicSite = models.ForeignKey("ComicSite")
    title = models.CharField(max_length = 255)
    html = models.TextField()
    