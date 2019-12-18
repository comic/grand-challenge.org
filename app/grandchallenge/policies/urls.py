from django.urls import path

from grandchallenge.policies.views import PolicyDetail

app_name = "policies"

urlpatterns = [path("<slug>/", PolicyDetail.as_view(), name="detail")]
