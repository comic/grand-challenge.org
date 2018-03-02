from django.conf.urls import url

from pages.views import page

urlpatterns = [
        url(r'^$', page, name='challenge-page'),
]
