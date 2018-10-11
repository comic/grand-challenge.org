from django.urls import path

from grandchallenge.statistics.views import StatisticsDetail

app_name = "statistics"

urlpatterns = [path("", StatisticsDetail.as_view(), name="detail")]
