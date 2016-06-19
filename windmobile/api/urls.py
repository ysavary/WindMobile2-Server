from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from .views import *

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/doc/#!/stations', permanent=True)),

    url(r'^stations/$', Stations.as_view(), name='api.stations'),
    url(r'^stations/json-doc/$', StationJsonDoc.as_view(), name='api.station_json_doc'),
    url(r'^stations/historic/json-doc/$', StationHistoricJsonDoc.as_view(), name='api.station_historic_json_doc'),
    url(r'^stations/(?P<station_id>.+)/historic/$', StationHistoric.as_view(), name='api.station_historic'),
    url(r'^stations/(?P<station_id>.+)/$', Station.as_view(), name='api.station'),

    url(r'^auth/login/$', AuthenticationLogin.as_view(), name='api.auth_login'),

    url(r'^users/profile/$', UserProfile.as_view(), name='api.user_profile'),
    url(r'^users/profile/favorites/(?P<station_id>.+)/$', UserProfileFavorite.as_view(),
        name='api.user_profile_favorites')
)
