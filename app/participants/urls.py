from django.conf.urls import url

from participants.views import (
    ParticipantRegistration,
    _register,
    RegistrationRequestList,
    RegistrationRequestCreate,
)

urlpatterns = [
    url(r'^registration/$', RegistrationRequestList.as_view(),
        name='registration-list'),
    url(r'^registration/create/$', RegistrationRequestCreate.as_view(),
        name='registration-create'),

    url(r'^register/$', ParticipantRegistration.as_view(),
        name='registration'),

    url(r'^_register/$', _register, name='registration-request'),
]
