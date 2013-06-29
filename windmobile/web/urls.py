from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/web/stations/', permanent=True)),
    url(r'^stations/$', views.station_list, name='web.station_list'),
    url(r'^stations/(?P<id>.+)/data/$', views.station_data, name='web.station_data'),
    url(r'^stations/(?P<id>.+)/$', views.station_info, name='web.station_info'),
)
