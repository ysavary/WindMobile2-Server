from django.conf.urls import patterns, url
from django.views.generic import RedirectView

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='stations/', permanent=True)),
    url(r'^stations/(?P<single_page_urls>.*)$', views.stations, name='web.stations'),
)
