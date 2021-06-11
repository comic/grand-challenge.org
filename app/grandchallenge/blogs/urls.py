from django.urls import path

from grandchallenge.blogs.views import PostDetail, PostList, PostTagList

app_name = "blogs"

urlpatterns = [
    path("", PostList.as_view(), name="list"),
    path("tag/<slug>/", PostTagList.as_view(), name="tag-list"),
    path("<slug>/", PostDetail.as_view(), name="detail"),
]
