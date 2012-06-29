from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^login/$','django.contrib.auth.views.login',{'template_name':'account/login.html'}),
    url(r'^logout/$','django.contrib.auth.views.logout',{'template_name':'account/logged_out.html'}),
    url(r'^password_change/$','django.contrib.auth.views.password_change',{'template_name':'account/password_change_form.html'}),
    url(r'^password_change/done/$','django.contrib.auth.views.password_change_done',{'template_name':'account/password_change_done.html'}),
)

