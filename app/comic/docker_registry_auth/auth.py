from pathlib import Path
from time import time
import jwt
from django.http import HttpResponse, HttpRequest, JsonResponse


def handle_auth(request: HttpRequest):
    scope = request.GET.get('scope')
    print(request.headers)
    path = Path('/home/tom/Projects/eyra/registry/registry.key')
    with open(path, 'r') as file:
        key = file.read()
    payload = {
        'iss': 'registry-token-issuer',
        'sub': 'tom',
        'aud': 'token-service',
        'exp': int(time()) + 30 * 24 * 3600,
    }

    if scope:
        payload['access'] = [
            {
                'type': 'repository',
                'name': 'alpine',
                'actions': ['pull', 'push']
            }
        ]

    jwt_token = jwt.encode(payload, key, headers={'kid': 'FUM4:HU2A:FT6Z:YKJH:G5YN:YIF2:KBKS:VLG6:HIR4:6JZJ:6MLJ:2OE2'}, algorithm='ES256')
    print(jwt_token.decode('utf-8'))
    # return HttpResponse(jwt_token.decode('utf-8'))
    return JsonResponse({
        'token': jwt_token.decode('utf-8')
    })

