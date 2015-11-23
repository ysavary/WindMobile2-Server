from calendar import timegm
from datetime import datetime

from rest_framework_jwt.compat import get_username
from rest_framework_jwt.settings import api_settings


def jwt_payload_handler(user):
    payload = {
        'username': get_username(user),
        'exp': datetime.utcnow() + api_settings.JWT_EXPIRATION_DELTA
    }

    # Include original issued at time for a brand new token,
    # to allow token refresh
    if api_settings.JWT_ALLOW_REFRESH:
        payload['orig_iat'] = timegm(
            datetime.utcnow().utctimetuple()
        )

    return payload
