import os
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from pymongo import MongoClient, uri_parser

from windmobile.api import diacritics


@api_view(['GET'])
def api_root(request):
    return Response({
        'List': reverse('station_list', request=request),
        'Mauborget': reverse('station_info', ['jdc-1001'], request=request),
        'Zinal': reverse('station_data', ['jdc-1003'], request=request),
    })


@api_view(['GET'])
def station_list(request):
    query = request.GET.get('query')
    if query:
        regexp_query = diacritics.create_regexp(diacritics.normalize(query))
        return Response(mongo_db.stations.find({'$or': [{'name': {'$regex': regexp_query, '$options': 'i'}},
                                                        {'short-name': {'$regex': regexp_query, '$options': 'i'}},
                                                        {'tags': query}]}))
    else:
        return Response(mongo_db.stations.find())


@api_view(['GET'])
def station_info(request, id):
    station_info = mongo_db.stations.find_one(id)
    if station_info:
        return Response(station_info)
    else:
        return Response({'detail': "No station with id '%s'" % id}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def station_data(request, id):
        if id in mongo_db.collection_names():
            return Response(mongo_db[id].find().sort('_id', -1).limit(1))
        else:
            return Response({'detail': "No collection with name '%s'" % id}, status=status.HTTP_404_NOT_FOUND)


mongo_url = os.environ['WINDMOBILE_MONGO_URL']
uri = uri_parser.parse_uri(mongo_url)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]