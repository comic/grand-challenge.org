from django.conf.urls import include, url

urlpatterns = [
    url(r'^profile/edit/', 'profiles.views.profile_edit',
        name='profile_redirect_edit'),
    url(r'^profile/', 'profiles.views.profile', name='profile_redirect'),
    url(r'^', include('userena.urls')),
]
