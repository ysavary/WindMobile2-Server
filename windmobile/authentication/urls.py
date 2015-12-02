from django.conf.urls import patterns, url

from .facebook_views import FacebookOauth2Callback
from .google_views import GoogleOauth2Callback


urlpatterns = patterns(
    '',
    url(r'^google/oauth2callback/$', GoogleOauth2Callback.as_view(), name='auth.google_oauth2callback'),
    url(r'^facebook/oauth2callback/$', FacebookOauth2Callback.as_view(), name='auth.facebook_oauth2callback')
)
