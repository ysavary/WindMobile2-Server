import os
from django.http.response import HttpResponseBadRequest
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.reverse import reverse
from pymongo import MongoClient, uri_parser

from windmobile.api import diacritics


@api_view(['GET'])
def api_root(request):
    return Response({
        'List': reverse('api.station_list', request=request),
        'Mauborget': reverse('api.station_info', ['jdc-1001'], request=request),
        'Zinal': reverse('api.station_data', ['jdc-1003'], request=request),
    })


@api_view(['GET'])
def station_list(request):
    search = request.QUERY_PARAMS.get('search')
    latitude = request.QUERY_PARAMS.get('lat')
    longitude = request.QUERY_PARAMS.get('lon')
    distance = request.QUERY_PARAMS.get('distance')
    word = request.QUERY_PARAMS.get('word')
    language = request.QUERY_PARAMS.get('language', 'english')

    if not (search or latitude or longitude or distance or word):
        return Response(mongo_db.stations.find())

    elif search and not (latitude or longitude or distance or word):
        regexp_query = diacritics.create_regexp(diacritics.normalize(search))
        return Response(mongo_db.stations.find({'$or': [{'name': {'$regex': regexp_query, '$options': 'i'}},
                                                        {'short': {'$regex': regexp_query, '$options': 'i'}},
                                                        {'tags': search}]}))

    elif latitude and longitude and distance and not (search or word):
        return Response(mongo_db.stations.find({
                                               'loc': {
                                                   '$near': {
                                                       '$geometry': {
                                                           'type': 'Point',
                                                           'coordinates': [float(latitude), float(longitude)]
                                                       },
                                                       '$maxDistance': int(distance)
                                                   }
                                               }}))

    elif word and not (search or latitude or longitude or distance):
        return Response(mongo_db.command('text', 'stations', search=word, language=language).get('results', []))

    else:
        raise ParseError(u"Invalid query parameters")


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