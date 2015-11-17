from django.conf.urls import patterns, url

from django.views.generic import RedirectView
from .views import *

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/doc/#!/stations')),
    url(r'^stations/$', Stations.as_view(), name='api.stations'),
    url(r'^stations/station_json_doc/$', Doc.as_view(), name='api.station_json_doc'),
    url(r'^stations/(?P<station_id>.+)/historic/$', Historic.as_view(), name='api.station_historic'),
    url(r'^stations/(?P<station_id>.+)/$', Station.as_view(), name='api.station'),
)
