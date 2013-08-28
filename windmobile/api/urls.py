from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.api_root),
    url(r'^stations/$', views.stations, name='api.stations'),
    url(r'^stations/(?P<id>.+)/historic/$', views.historic, name='api.historic'),
    url(r'^stations/(?P<id>.+)/$', views.station, name='api.station'),
)
