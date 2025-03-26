import functools
from datetime import timedelta

import boto3
from django.db.backends.postgresql import base
from django.utils import timezone


def thread_local_cache(ttl, max_size=128):
    def decorator(func):
        function_cache = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            current_time = timezone.now()

            if key in function_cache:
                result, timestamp = function_cache[key]
                if (current_time - timestamp) < ttl:
                    return result

            expired_keys = [
                k
                for k, (_, timestamp) in function_cache.items()
                if (current_time - timestamp) >= ttl
            ]
            for expired_key in expired_keys:
                del function_cache[expired_key]

            if len(function_cache) >= max_size:
                oldest_key = min(
                    function_cache, key=lambda k: function_cache[k][1]
                )
                del function_cache[oldest_key]

            result = func(*args, **kwargs)
            function_cache[key] = (result, current_time)

            return result

        return wrapper

    return decorator


@thread_local_cache(
    # The auth tokens expire after 15 minutes and should be reused
    # See https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html#UsingWithRDS.IAMDBAuth.Limitations
    ttl=timedelta(minutes=10)
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
