from django.conf.urls import patterns, url
from django.views.generic import RedirectView, TemplateView

urlpatterns = patterns(
    '',
    url(r'^$', RedirectView.as_view(url='stations/', permanent=True)),
    url(r'^stations/', TemplateView.as_view(template_name='stations.html'), name='web.stations'),
)
