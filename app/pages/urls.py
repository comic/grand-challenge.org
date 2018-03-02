from django.conf.urls import url

from pages.views import page, insertedpage

urlpatterns = [
        url(r'^$', page, name='challenge-page'),
        url(r'^insert/(?P<dropboxpath>.+)/$', insertedpage,
            name='challenge-insertedpage'),
]
