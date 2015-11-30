from django.conf.urls import patterns, url
from .google_views import GoogleOauth2Callback


urlpatterns = patterns(
    '',
    url(r'^google/oauth2callback/$', GoogleOauth2Callback.as_view(), name='auth.google_oauth2callback')
)
