import os
from urlparse import urljoin

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
        'Search': urljoin(reverse('api.station_list', request=request), u"?search=dole"),
        'Geo search': urljoin(reverse('api.station_list', request=request), u"?lat=46.78&lon=6.63&distance=20000"),
        'Text search': urljoin(reverse('api.station_list', request=request), u"?word=sommet"),
        'Mauborget': reverse('api.station', ['jdc-1001'], request=request),
        'Historic Mauborget': reverse('api.historic', ['jdc-1001'], request=request),
    })


@api_view(['GET'])
def station_list(request):
    search = request.QUERY_PARAMS.get('search')
    latitude = request.QUERY_PARAMS.get('lat')
    longitude = request.QUERY_PARAMS.get('lon')
    distance = request.QUERY_PARAMS.get('distance')
    word = request.QUERY_PARAMS.get('word')
    language = request.QUERY_PARAMS.get('language', 'english')
    limit = int(request.QUERY_PARAMS.get('limit', 20))

    if not (search or latitude or longitude or distance or word):
        return Response(mongo_db.stations.find().limit(limit))

    elif search and not (latitude or longitude or distance or word):
        regexp_query = diacritics.create_regexp(diacritics.normalize(search))
        return Response(mongo_db.stations.find({'$or': [{'name': {'$regex': regexp_query, '$options': 'i'}},
                                                        {'short': {'$regex': regexp_query, '$options': 'i'}},
                                                        {'tags': search}]}).limit(limit))

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
                                               }}).limit(limit))

    elif word and not (search or latitude or longitude or distance):
        return Response(mongo_db.command('text', 'stations', search=word, language=language).get('results', []))

    else:
        raise ParseError(u"Invalid query parameters")


@api_view(['GET'])
def station(request, id):
    station_info = mongo_db.stations.find_one(id)
    if station_info:
        return Response(station_info)
    else:
        return Response({'detail': "No station with id '%s'" % id}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def historic(request, id):
        if id in mongo_db.collection_names():
            return Response(mongo_db[id].find().sort('_id', -1).limit(10))
        else:
            return Response({'detail': "No historic data for id '%s'" % id}, status=status.HTTP_404_NOT_FOUND)


mongo_url = os.environ['WINDMOBILE_MONGO_URL']
uri = uri_parser.parse_uri(mongo_url)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]