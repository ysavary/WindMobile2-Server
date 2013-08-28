from django.views import generic


class StationsView(generic.TemplateView):
    template_name = "stations.html"

stations = StationsView.as_view()


class MapView(generic.TemplateView):
    template_name = "map.html"

map = MapView.as_view()
