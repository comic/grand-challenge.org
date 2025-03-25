import boto3
from django.db.backends.postgresql import base


class DatabaseWrapper(base.DatabaseWrapper):
    def get_connection_params(self):
        params = super().get_connection_params()

        if params.pop("use_iam_auth"):
            rds_client = boto3.client("rds")
            params["password"] = rds_client.generate_db_auth_token(
                DBHostname=params["host"],
                Port=params["port"],
                DBUsername=params["user"],
            )

        return params
