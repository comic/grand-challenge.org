from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.template.response import TemplateResponse
from django.views.generic import TemplateView

from comicsite.views import comicmain
from uploads.views import serve

admin.autodiscover()

def handler500(request):
    context = {'request': request}
    template_name = '500.html'
    return TemplateResponse(request, template_name, context, status=500)

urlpatterns = [

    # main page
    url(r'^$', comicmain, name='home'),

    url(
        r'^robots\.txt/$',
        TemplateView.as_view(
            template_name='robots.txt',
            content_type='text/plain',
        ),
    ),

    url(settings.ADMIN_URL, admin.site.urls),

    url(r'^site/', include('comicsite.urls'), name='site'),

    # Do not change the namespace without updating the view names in
    # evaluation.serializers
    url(r'^api/', include('api.urls', namespace='api')),

    # Used for logging in and managing profiles. This is done on the framework
    # level because it is too hard to get this all under each project
    url(r'^accounts/', include('profiles.urls')),
    url(r'^socialauth/', include('social_django.urls', namespace='social')),

    url(r'^challenges/', include('challenges.urls', namespace='challenges')),

    # ========== catch all ====================
    # when all other urls have been checked, try to load page from main project
    # keep this url at the bottom of this list, because urls are checked in
    # order
    url(r'^(?P<page_title>[\w-]+)/$', comicmain, name='mainproject-home'),

    url(r'^media/(?P<project_name>[\w-]+)/(?P<path>.*)$', serve),

]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
                      url(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns
