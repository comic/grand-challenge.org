from django.urls import path

from grandchallenge.timezones.views import SetTimezone

app_name = "timezones"

urlpatterns = [path("set/", SetTimezone.as_view(), name="set")]
