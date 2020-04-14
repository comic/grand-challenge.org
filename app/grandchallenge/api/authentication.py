from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """
    Some clients only support setting Bearer tokens, so support them by
    changing the keyword.
    """

    keyword = "Bearer"
