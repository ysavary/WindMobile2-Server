from django.conf.urls import patterns, url

urlpatterns = patterns('api.views',
    url(r'^$', 'api_root'),
    url(r'^station/$', 'station_list', name='station-list'),
    url(r'^station/(?P<id>.+)$', 'station_detail', name='station-detail')
)
