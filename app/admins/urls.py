from django.conf.urls import url

from admins.views import AdminsList

urlpatterns = [
    url(r'^$', AdminsList.as_view(), name='list'),
]
