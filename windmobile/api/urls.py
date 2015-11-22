from django.conf.urls import patterns, url

from django.views.generic import RedirectView
from rest_framework.authtoken import views as auth_rest_views

from .views import *

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/doc/#!/stations', permanent=True)),

    url(r'^stations/$', Stations.as_view(), name='api.stations'),
    url(r'^stations/json-doc/$', StationJsonDoc.as_view(), name='api.station_json_doc'),
    url(r'^stations/historic/json-doc/$', StationHistoricJsonDoc.as_view(), name='api.station_historic_json_doc'),
    url(r'^stations/(?P<station_id>.+)/historic/$', StationHistoric.as_view(), name='api.station_historic'),
    url(r'^stations/(?P<station_id>.+)/$', Station.as_view(), name='api.station'),

    url(r'^users/login', auth_rest_views.obtain_auth_token, name='api.user_login'),
    url(r'^users/profile/$', UserProfile.as_view(), name='api.user_profile')
)
