import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission


class JWTAuthentication(BaseAuthentication):

    def get_jwt_value(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION').split()
        if not auth:
            return None

        if len(auth) == 1:
            raise AuthenticationFailed("Invalid Authorization header: no credentials provided")
        elif len(auth) > 2:
            raise AuthenticationFailed("Invalid Authorization header: credentials string should not contain spaces")

        return auth[1]

    def authenticate(self, request):
        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            return None

        try:
            payload = jwt.decode(jwt_value, settings.SECRET_KEY)
        except jwt.ExpiredSignature:
            raise AuthenticationFailed("Signature has expired")
        except jwt.DecodeError:
            raise AuthenticationFailed("Error decoding signature")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed()

        return payload['username'], jwt_value


class IsJWTAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.user
