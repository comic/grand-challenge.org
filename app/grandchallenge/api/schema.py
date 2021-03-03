from drf_spectacular.extensions import OpenApiAuthenticationExtension
from knox.settings import knox_settings


class KnoxTokenScheme(OpenApiAuthenticationExtension):
    target_class = "knox.auth.TokenAuthentication"
    name = "tokenAuth"
    match_subclasses = True
    priority = -1

    def get_security_definition(self, auto_schema):
        prefix = knox_settings.AUTH_HEADER_PREFIX
        if prefix == "Bearer":
            return {
                "type": "http",
                "scheme": "bearer",
            }
        else:
            return {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": f'Token-based authentication with required prefix "{prefix}"',
            }
