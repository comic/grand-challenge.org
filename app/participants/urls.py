from django.conf.urls import url

from participants.views import ParticipantRegistration, _register

urlpatterns = [
    url(r'^registration/$', ParticipantRegistration.as_view(),
        name='participant-registration'),

    url(r'^_register/$', _register, name='participant-registration-request'),
]
