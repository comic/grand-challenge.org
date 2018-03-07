from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import get_objects_for_user

from comicmodels.models import UploadModel


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

        return get_objects_for_user(request.user, self.permission_name,
                                    klass=UploadModel.objects)


admin.site.register(UploadModel, UploadModelAdmin)
