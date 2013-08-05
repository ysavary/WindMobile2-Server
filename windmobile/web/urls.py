from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/web/stations/', permanent=True)),
    url(r'^stations/$', views.station_list, name='web.station_list'),
)
