from threading import Lock

import boto3
from cachetools import TTLCache, cached
from django.db.backends.postgresql import base


@cached(
    # The auth tokens expire after 15 minutes and should be reused
    # See https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html#UsingWithRDS.IAMDBAuth.Limitations
    cache=TTLCache(maxsize=64, ttl=600),
    lock=Lock(),
)
def generate_db_auth_token(*, host, port, user):
    rds_client = boto3.client("rds")
    return rds_client.generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=user,
    )


class DatabaseWrapper(base.DatabaseWrapper):
    def get_connection_params(self):
        params = super().get_connection_params()

        if params.pop("use_iam_auth"):
            params["password"] = generate_db_auth_token(
                host=params["host"],
                port=params["port"],
                user=params["user"],
            )

        return params

    def init_connection_state(self):
        super().init_connection_state()

        with self.connection.cursor() as cursor:
            # wait 100ms to acquire DB lock rather than indefinitely,
            # this saves having to set select_for_update() on normal views
            cursor.execute("SET lock_timeout = 100;")
