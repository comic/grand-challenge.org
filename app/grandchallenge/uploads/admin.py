from django.contrib import admin

from grandchallenge.uploads.models import PublicMedia, UploadModel

admin.site.register(UploadModel)
admin.site.register(PublicMedia)
