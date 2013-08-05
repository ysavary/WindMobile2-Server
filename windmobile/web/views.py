from django.views import generic


class StationList(generic.TemplateView):
    template_name = "station_list.html"

station_list = StationList.as_view()
