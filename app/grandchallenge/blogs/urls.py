from django.urls import path

from grandchallenge.blogs.views import PostDetail, PostList

app_name = "blogs"

urlpatterns = [
    path("", PostList.as_view(), name="list"),
    path("<slug>/", PostDetail.as_view(), name="detail"),
]
