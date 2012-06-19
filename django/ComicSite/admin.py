'''
Created on Jun 18, 2012

@author: Sjoerd
'''

from django.contrib import admin
from models import ComicSite,Page

admin.site.register(ComicSite)



class PageAdmin(admin.ModelAdmin):
    """Define the admin interface for pages"""
    
    #Show these page params in admin overview list 
    list_display = ('title','ComicSite')
    ordering = ['ComicSite']
        
    

admin.site.register(Page,PageAdmin)    