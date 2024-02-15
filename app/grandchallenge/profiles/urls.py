from django.urls import path, re_path

from grandchallenge.groups.views import UserAutocomplete
from grandchallenge.profiles.views import (
    NewsletterSignUp,
    NewsletterUnsubscribeView,
    NotificationUnsubscribeView,
    SubscriptionOverview,
    UserProfileDetail,
    UserProfileUpdate,
    profile,
)

urlpatterns = [
    path(
        "user-autocomplete/",
        UserAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    re_path(
        r"newsletter/unsubscribe/(?P<token>[\w:\-_=]+)/$",
        NewsletterUnsubscribeView.as_view(),
        name="newsletter-unsubscribe",
    ),
    re_path(
        r"notifications/unsubscribe/(?P<token>[\w:\-_=]+)/$",
        NotificationUnsubscribeView.as_view(),
        name="notification-unsubscribe",
    ),
    re_path(
        r"subscription-overview/(?P<token>[\w:\-_=]+)/$",
        SubscriptionOverview.as_view(),
        name="subscriptions",
    ),
    path("profile/", profile, name="profile-detail-redirect"),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/$",
        UserProfileDetail.as_view(),
        name="profile-detail",
    ),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/edit/$",
        UserProfileUpdate.as_view(),
        name="profile-update",
    ),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/newsletter-sign-up/$",
        NewsletterSignUp.as_view(),
        name="newsletter-sign-up",
    ),
]
