from django.contrib import admin, messages
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user

from comicmodels.models import UploadModel, RegistrationRequest, ProjectMetaData
from comicsite.models import send_participation_request_rejected_email, send_participation_request_accepted_email


class ComicModelAdmin(GuardedModelAdmin):
    """Base class for ComicModel admin. Handles common functionality like setting permissions"""

    # if user has this permission, user can access this ComicModel.
    permission_name = 'view_ComicSiteModel'

    def __init__(self, model, admin_site):
        super(GuardedModelAdmin, self).__init__(model, admin_site)

        # use general template instead of the one GuardedModelAdmin puts in there
        # because I do not want to show the object permissions button project
        # admins 
        self.change_form_template = 'admin/change_form.html'

    def save_model(self, request, obj, form, change):
        obj.save()

    def get_queryset(self, request):
        """ overwrite this method to return only pages comicsites to which current user has access 
            
            note: GuardedModelAdmin can also restrict queryset to owned by user only, but this
            needs a 'user' field for each model, which I don't want because we use permission
            groups and do not restrict to user owned only.
        """
        try:
            user_qs = self.defaultQuerySet(request)
        except (ObjectDoesNotExist, TypeError):
            return UploadModel.objects.none()
        return user_qs

    def defaultQuerySet(self, request):
        """ Overwrite this method in child classes to make sure instance of that class is passed to 
            get_objects_for_users """

        return get_objects_for_user(request.user, self.permission_name, self)


class UploadModelAdmin(ComicModelAdmin):
    list_display = ('title', 'file', 'comicsite', 'user', 'created')
    list_filter = ['comicsite']

    # explicitly inherit manager because this is not done by default with non-abstract superclass
    # see https://docs.djangoproject.com/en/dev/topics/db/managers/#custom-managers-and-model-inheritance
    _default_manager = UploadModel.objects

    def defaultQuerySet(self, request):
        """ Overwrite this method in child classes to make sure instance of that class is passed to 
        get_objects_for_users """

        return get_objects_for_user(request.user, self.permission_name, klass=UploadModel.objects)


class RegistrationRequestAdmin(admin.ModelAdmin):
    # TODO: This class should derive from ComicModelAdmin and not from GuardedModelAdmin

    # if user has this permission, user can access this ComicModel.
    permission_name = 'view_ComicSiteModel'

    list_display = (
    'user', 'user_email', 'user_real_name', 'user_affiliation', 'project', 'created', 'changed', 'status')
    # list_display = ('email', 'first_name', 'last_name')
    # list_filter = ('is_staff', 'is_superuser', 'is_active')
    readonly_fields = ("user", "project", 'created', 'changed', 'user_email', 'user_real_name', 'user_affiliation')
    actions = ['accept', 'reject']

    def save_model(self, request, obj, form, change):
        """ called when directly editing RegistrationRequest 
        
        """

        self.process_status_change(request, obj)
        super(RegistrationRequestAdmin, self).save_model(request, obj, form, change)

    def get_queryset(self, request):
        """ overwrite this method to return only pages comicsites to which current user has access 
            
            note: GuardedModelAdmin can also restrict queryset to owned by user only, but this
            needs a 'user' field for each model, which I don't want because we use permission
            groups and do not restrict to user owned only.
        """

        # TODO: This way of filtering should be used for all comicobjects, this
        #       would be a lot of rafactoring.                   
        qs = super(RegistrationRequestAdmin, self).get_queryset(request)

        if not request.is_projectadmin:
            if request.user.is_superuser:
                # in general registration_requests overview, show requests for all
                # projects only to admin
                return qs
            else:
                return RegistrationRequest.objects.none()

        else:
            # show only requests for the current project
            qs_out = qs.filter(project__pk=request.project_pk)

        return qs_out

    def process_status_change(self, request, obj):

        if obj.has_changed('status'):
            if obj.status == RegistrationRequest.ACCEPTED:
                self.process_acceptance(request, obj)
            if obj.status == RegistrationRequest.REJECTED:
                self.process_rejection(request, obj)
        else:
            messages.add_message(request, messages.INFO, 'Status of {0}\
                                 did not change. No actions taken'.format(str(obj)))

    def process_acceptance(self, request, obj):
        obj.status = RegistrationRequest.ACCEPTED

        obj.changed = timezone.now()
        obj.save()

        obj.project.add_participant(obj.user)
        messages.add_message(request, messages.SUCCESS, 'User "' + obj.user.username + '"\
                                         is now a participant for ' + obj.project.short_name +
                             ". An email has been sent to notify the user")

        send_participation_request_accepted_email(request, obj)

    def process_rejection(self, request, obj):
        obj.status = RegistrationRequest.REJECTED

        obj.changed = timezone.now()
        obj.save()

        obj.project.remove_participant(obj.user)
        messages.add_message(request, messages.WARNING, 'User "' + obj.user.username + '"\
                                         has been rejected as a participant for ' + obj.project.short_name +
                             ". An email has been sent to notify the user")

        send_participation_request_rejected_email(request, obj)

    def accept(self, request, queryset):
        """ called from admin actions dropdown in RegistrationRequests list 
        
        """
        for obj in queryset.all():
            obj.status = RegistrationRequest.ACCEPTED
            self.process_status_change(request, obj)

    def reject(self, request, queryset):
        """ called from admin actions dropdown in RegistrationRequests list 
        
        """
        for obj in queryset.all():
            obj.status = RegistrationRequest.REJECTED
            self.process_status_change(request, obj)


admin.site.register(RegistrationRequest, RegistrationRequestAdmin)
admin.site.register(UploadModel, UploadModelAdmin)
admin.site.register(ProjectMetaData)
