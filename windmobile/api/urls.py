from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.api_root),
    url(r'^stations/$', views.station_list, name='station_list'),
    url(r'^stations/(?P<id>.+)/data/$', views.station_data, name='station_data'),
    url(r'^stations/(?P<id>.+)/$', views.station_info, name='station_info'),
)
