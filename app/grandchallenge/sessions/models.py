from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models


class BrowserSession(AbstractBaseSession):
    user = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.CASCADE,
        null=True,
        editable=False,
        related_name="browser_sessions",
    )

    @classmethod
    def get_session_store_class(cls):
        return SessionStore


class SessionStore(DBStore):
    @classmethod
    def get_model_class(cls):
        return BrowserSession

    def create_model_instance(self, data):
        obj = super().create_model_instance(data)
        try:
            user_id = int(data.get("_auth_user_id"))
        except (ValueError, TypeError):
            user_id = None
        obj.user_id = user_id
        return obj
