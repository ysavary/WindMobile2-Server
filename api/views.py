import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status
from pymongo import Connection, uri_parser

import diacritics

@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'List': reverse('station-list', request=request),
        'Mauborget': reverse('station-detail', ['jdc_1001'], request=request),
        'Zinal': reverse('station-detail', ['jdc_1003'], request=request),
    })


@api_view(['GET'])
def station_list(request):
    if request.method == 'GET':
        query = request.GET.get('query')
        if query:
            regexp_query = diacritics.create_regexp(diacritics.normalize(query))
            return Response(mongo_db.stations.find({'$or': [{'name': {'$regex': regexp_query, '$options': 'i'}},
                                                            {'short-name': {'$regex': regexp_query, '$options': 'i'}},
                                                            {'tags': query}]}))
        else:
            return Response(mongo_db.stations.find())


@api_view(['GET'])
def station_detail(request, id):
    if request.method == 'GET':
        return Response(mongo_db.stations.find_one(id))


mongo_url = os.environ['WINDMOBILE_MONGO_URL']
connection = Connection(mongo_url)
db_name = uri_parser.parse_uri(mongo_url)['database']
mongo_db = connection[db_name]