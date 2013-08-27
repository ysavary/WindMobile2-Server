from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView

from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/$', RedirectView.as_view(url='2/', permanent=True)),
    url(r'^api/2/', include('windmobile.api.urls')),
    url(r'^', include('windmobile.web.urls')),
)
