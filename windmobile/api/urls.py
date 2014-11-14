from django.conf.urls import patterns, url

from . import views
from django.views.generic import RedirectView

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/doc/#!/stations')),
    url(r'^stations/$', views.stations, name='api.stations'),
    url(r'^stations/station_json_doc/$', views.station_json_doc, name='api.station_json_doc'),
    url(r'^stations/(?P<station_id>.+)/historic/$', views.station_historic, name='api.station_historic'),
    url(r'^stations/(?P<station_id>.+)/$', views.station, name='api.station'),
)
