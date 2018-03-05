from django.conf.urls import url

from participants.views import ParticipantRegistration, _register, \
    RegistrationRequestList

urlpatterns = [
    url(r'^registration/$', RegistrationRequestList.as_view(),
        name='registration-list'),

    url(r'^register/$', ParticipantRegistration.as_view(),
        name='registration'),

    url(r'^_register/$', _register, name='registration-request'),
]
