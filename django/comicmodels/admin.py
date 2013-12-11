import datetime

from exceptions import AttributeError,Exception

from django import forms
from django.db import models
from django.conf import settings
from django.contrib import admin,messages
from django.contrib.admin.util import unquote
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ObjectDoesNotExist

from dropbox import client, rest, session
from dropbox.rest import ErrorResponse
from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user
from comicmodels.models import FileSystemDataset,UploadModel,DropboxFolder,RegistrationRequest
from comicsite.models import ComicSiteException,send_participation_request_rejected_email,send_participation_request_accepted_email


class ComicModelAdmin(GuardedModelAdmin):
    """Base class for ComicModel admin. Handles common functionality like setting permissions"""
    
    # if user has this permission, user can access this ComicModel.
    permission_name = 'view_ComicSiteModel'
    
    def save_model(self, request, obj, form, change):        
        obj.save()
    
    
    def queryset(self, request): 
        """ overwrite this method to return only pages comicsites to which current user has access 
            
            note: GuardedModelAdmin can also restrict queryset to owned by user only, but this
            needs a 'user' field for each model, which I don't want because we use permission
            groups and do not restrict to user owned only.
        """
        try:
            user_qs = self.defaultQuerySet(request)
        except ObjectDoesNotExist as e:
            return UploadModel.objects.none()
        return user_qs
    
    def defaultQuerySet(self,request):
        """ Overwrite this method in child classes to make sure instance of that class is passed to 
            get_objects_for_users """ 
        
        return get_objects_for_user(request.user, self.permission_name,self)
    
        
        
class FileSystemDatasetForm(forms.ModelForm):
                
    folder = forms.CharField(widget=forms.TextInput(attrs={'size': 60}),help_text = "All files for this dataset are stored in this folder on disk")
    folder.required = False    
    
    #TODO: print {% tag %} values in this
    tag = forms.CharField(widget=forms.TextInput(attrs={'size': 60, 'readonly':'readonly'}),help_text = "To show all files in this dataset as downloads on a page, copy-paste this tag into the page contents")
    
    def __init__(self, *args, **kwargs):
        # only change attributes if an instance is passed                    
        instance = kwargs.get('instance')
        
        if instance:
            self.base_fields['tag'].initial = instance.get_template_tag()
        
            #self.base_fields['calculated'].initial = (instance.bar == 42)
        forms.ModelForm.__init__(self, *args, **kwargs)

    
    class Meta:       
       model = FileSystemDataset
       
        

class FileSystemDatasetInitialForm(forms.ModelForm):
    """ In initial form, do not show folder edit field """                    
    class Meta:
        exclude = ['folder',]        
        model = FileSystemDataset        


class FileSystemDatasetAdmin(ComicModelAdmin):    
    """ On initial creation, do not show the folder dialog because it is initialized to a default value"""
        
    list_display = ('title','description','get_tag','comicsite')
    form = FileSystemDatasetForm
    
    # explicitly inherit manager because this is not done by default with non-abstract superclass
    # see https://docs.djangoproject.com/en/dev/topics/db/managers/#custom-managers-and-model-inheritance
    _default_manager = FileSystemDataset.objects
    
    def get_tag(self,obj):
        return obj.get_template_tag()
    
    def get_form(self, request, obj=None, **kwargs):        
        if obj:
            
            return FileSystemDatasetForm
        else:
            return FileSystemDatasetInitialForm
    
    def defaultQuerySet(self,request):
       """ Overwrite this method in child classes to make sure instance of that class is passed to 
       get_objects_for_users """         
              
       return get_objects_for_user(request.user, self.permission_name, klass=FileSystemDataset.objects)
    
    
        
class UploadModelAdmin(ComicModelAdmin):

    list_display = ('title','file','comicsite','user','created')
    list_filter = ['comicsite']
    
    # explicitly inherit manager because this is not done by default with non-abstract superclass
    # see https://docs.djangoproject.com/en/dev/topics/db/managers/#custom-managers-and-model-inheritance
    _default_manager = UploadModel.objects
    
    def defaultQuerySet(self,request):
       """ Overwrite this method in child classes to make sure instance of that class is passed to 
       get_objects_for_users """         
              
       return get_objects_for_user(request.user, self.permission_name, klass=UploadModel.objects)
    

class DropboxFolderForm(forms.ModelForm):

    class Meta:
        exclude = ['access_token_key','access_token_secret','last_status_msg']        
        model = DropboxFolder        


class DropboxFolderAdmin(ComicModelAdmin):
    
    readonly_fields = ('connection_status','template_tag')
    list_display = ('descr','last_status_msg','template_tag')
    
    
    def descr(self,obj):
        """Show info if connected, "not connected" otherwise 
        """
        if obj.title != "":
            return obj.title
        else:
            return "not connected"
    
    def template_tag(self,obj):
        """ use this on page to show file contents from dropbox
        """
        if obj.title == "":
            return "not available"
        else:
            return "{% dropbox title:"+obj.title+" file:<filepath> %}"
    
        
        
    def connection_status(self,obj):
                
        if not obj.pk:
            
            message = "<span class='errors'>Please save and reload to continue connecting to\
                       dropbox </span>"
      
        else:
            (status,status_msg) = obj.get_connection_status()            
            buttons = self.get_buttons_for_status(obj,status)
            infodiv =  "<div id='connection_status' class = 'grayedOut'> "+status_msg + "</div>"
            message =  infodiv + buttons +self.get_hidden_obj_id(obj)
            message = "<div id='dropbox_connection_area'> " + message + "</div>"
            
        return message
    
    def get_buttons_for_status(self,obj,status):
        """ Which buttons should be shown for current status of dropbox connection? Return html.        
        """
        HTML_AUTHBUTTON = "<button type='button' id='reset_connection'>Authorize connection</button>"
        HTML_RESETBUTTON = "<button type='button' id='reset_connection'>Reset connection</button>"
        HTML_REFRESHBUTTON = "<button type='button' id='refresh_connection'>Check connection now</button>"
        
        if status == obj.NOT_SAVED:
            buttons = ""
        elif status == obj.READY_FOR_AUTH:
            buttons = HTML_AUTHBUTTON
        elif status == obj.CONNECTED:
            buttons = HTML_RESETBUTTON + HTML_REFRESHBUTTON
        elif status == obj.ERROR:
            buttons = HTML_RESETBUTTON + HTML_REFRESHBUTTON
        else:
            buttons = HTML_RESETBUTTON + HTML_REFRESHBUTTON
            #raise ComicSiteException("Unknown status: '"+status+"' I don't know which buttons to show")
         
        return buttons
        
    
    def get_hidden_obj_id(self,obj):
        """ Jquery needs to know the id of the current object. This method renders a hidden
            html element which Jquery can read. If you know a better way let me know:
            sjoerdk@home.nl 
        """
        return "<span id='obj_id_span' value='"+str(obj.id)+"' style='display:none;'></span>"
        
    
    def get_autorization_link(self,obj):
        
        try:
            app_key = settings.DROPBOX_APP_KEY
            app_secret = settings.DROPBOX_APP_SECRET
            access_type = settings.DROPBOX_ACCESS_TYPE
        except AttributeError as e:
            
            return "ERROR: A key required for this app to connect to dropbox could not be found in settings..\
                    Has this been forgotten?. Original error: "+ str(e)
        
        sess = session.DropboxSession(app_key, app_secret, access_type)
        request_token = sess.obtain_request_token()
        url = sess.build_authorize_url(request_token)
        
        #    except Exception as e:
        #    return "An error occured while autorizing with dropbox: " + str(e)

        link = "<a href =\""+ url + "\"> Allow access to your dropbox folder</a>"
        
        return link
    
        
    
    # Allow HTML rendering for this function
    connection_status.allow_tags = True
    
     
    # explicitly inherit manager because this is not done by default with non-abstract superclass
    # see https://docs.djangoproject.com/en/dev/topics/db/managers/#custom-managers-and-model-inheritance
    _default_manager = DropboxFolder.objects    
    form = DropboxFolderForm
    
    def defaultQuerySet(self,request):
       """ Overwrite this method in child classes to make sure instance of that class is passed to 
       get_objects_for_users """         
              
       return get_objects_for_user(request.user, self.permission_name, klass=DropboxFolder.objects)
    
    class Media:
        js = ("js/django_dropbox/admin_add_callback.js",)
            

        
class RegistrationRequestsAdmin(GuardedModelAdmin):    
    list_display = ('user','project', 'created', 'changed','status')
    #list_display = ('email', 'first_name', 'last_name')
    #list_filter = ('is_staff', 'is_superuser', 'is_active')
    readonly_fields=("user","project",'created','changed')
    actions = ['accept','reject']    
    
    
    def save_model(self, request, obj, form, change):
        """ called when directly editing RegistrationRequest 
        
        """
        
        self.process_status_change(request,obj)            
        super(RegistrationRequestsAdmin,self).save_model(request, obj, form, change)

    
    def process_status_change(self,request,obj):
        if obj.has_changed('status'):
            if obj.status == RegistrationRequest.ACCEPTED:
                self.process_acceptance(request,obj)
            if obj.status == RegistrationRequest.REJECTED:
                self.process_rejection(request,obj)
        else:
            messages.add_message(request, messages.INFO, 'Status of {0}\
                                 did not change. No actions taken'.format(str(obj)))
        
    def process_acceptance(self,request,obj):                        
        obj.status = RegistrationRequest.ACCEPTED
        obj.changed = datetime.datetime.today()
        obj.save()
        
        obj.project.add_participant(obj.user)                
        messages.add_message(request, messages.SUCCESS, 'User "'+obj.user.username+'"\
                                         is now a participant for '+ obj.project.short_name + 
                                         ". An email has been sent to notify the user")
        
        send_participation_request_accepted_email(request,obj)
               
    def process_rejection(self,request,obj):                        
        obj.status = RegistrationRequest.REJECTED
        obj.changed = datetime.datetime.today()
        obj.save()
        
        obj.project.remove_participant(obj.user)                
        messages.add_message(request, messages.WARNING, 'User "'+obj.user.username+'"\
                                         has been rejected as a participant for '+ obj.project.short_name + 
                                         ". An email has been sent to notify the user")
                
         
        send_participation_request_rejected_email(request,obj)

    
    
    def accept(self, request, queryset):
        """ called from admin actions dropdown in RegistrationRequests list 
        
        """                            
        for obj in queryset.all():
            obj.status = RegistrationRequest.ACCEPTED
            self.process_status_change(request,obj)            
                
        

    def reject(self, request, queryset):
        """ called from admin actions dropdown in RegistrationRequests list 
        
        """        
        for obj in queryset.all():
            obj.status = RegistrationRequest.REJECTED
            self.process_status_change(request,obj)
            

admin.site.register(RegistrationRequest,RegistrationRequestsAdmin)
admin.site.register(FileSystemDataset,FileSystemDatasetAdmin)
admin.site.register(UploadModel,UploadModelAdmin)
admin.site.register(DropboxFolder,DropboxFolderAdmin)
