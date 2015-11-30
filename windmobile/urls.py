from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView

from django.contrib import admin
from django.contrib.staticfiles import views

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/$', RedirectView.as_view(url='2/', permanent=True)),
    url(r'^api/2/', include('windmobile.api.urls')),
    url(r'^auth/', include('windmobile.authentication.urls')),
    url(r'^doc/', include('rest_framework_swagger.urls'))
)

if settings.DEBUG:
    urlpatterns += [
        url(r'^$', RedirectView.as_view(url='/stations/', permanent=True)),
        url(r'^stations/', views.serve, kwargs={
            'path': 'web/stations.html'
        })
    ]