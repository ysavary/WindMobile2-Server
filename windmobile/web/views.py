import os

from django.views import generic
from pymongo import MongoClient, uri_parser


class StationList(generic.TemplateView):
    template_name = "station_list.html"

    def get_context_data(self, **kwargs):
        context = super(StationList, self).get_context_data(**kwargs)
        context['station_list'] = mongo_db.stations.find()
        return context
station_list = StationList.as_view()


class StationData(generic.TemplateView):
    template_name = "station_data.html"

    def get_context_data(self, **kwargs):
        context = super(StationData, self).get_context_data(**kwargs)
        id = context['id']
        if id in mongo_db.collection_names():
            context['data'] = mongo_db[id].find().sort('_id', -1).limit(1)
        return context
station_data = StationData.as_view()


class StationInfo(generic.TemplateView):
    template_name = "station_list.html"

    def get_context_data(self, **kwargs):
        context = super(StationInfo, self).get_context_data(**kwargs)
        context['station_list'] = mongo_db.stations.find()
        return context
station_info = StationInfo.as_view()

mongo_url = os.environ['WINDMOBILE_MONGO_URL']
uri = uri_parser.parse_uri(mongo_url)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]
