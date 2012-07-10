'''
Created on Jun 18, 2012

@author: Sjoerd
'''

from django.contrib import admin
from django import forms
from django.db import models 

from guardian.admin import GuardedModelAdmin
from models import ComicSite,Page




class PageAdminForm(forms.ModelForm):
    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices=(
                         (models.BLANK_CHOICE_DASH[0]),
                         ('FIRST', 'First'),
                         ('UP', 'Up'),
                         ('DOWN', 'Down'),
                         ('LAST', 'Last'),
                        )
    class Meta:
        model = Page

class PageAdmin(GuardedModelAdmin):
    """Define the admin interface for pages"""
    form = PageAdminForm
    
    def save_model(self, request, obj, form, change):
        obj.save()
        move = form.cleaned_data['move']
        obj.move(move)
    
    #Show these page params in admin overview list 
    list_display = ('title','ComicSite','order')


class ComicSiteAdmin(GuardedModelAdmin):
    pass
    
    
        

admin.site.register(ComicSite,ComicSiteAdmin)
admin.site.register(Page,PageAdmin)


    

    
