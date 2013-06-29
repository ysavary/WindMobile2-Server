from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView

from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='/api/2/', permanent=True)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/2/', include('windmobile.api.urls')),
    url(r'^web/', include('windmobile.web.urls')),
)
