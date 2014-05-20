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
    return Response({'API documentation (default limit=10)': [
        {
            'List 100 stations':
                urljoin(reverse('api.stations', request=request), '?limit=100')
        },
        {
            'Search (ignore accents)':
                urljoin(reverse('api.stations', request=request), '?search=dole')
        },
        {
            'Geo search 3 stations around Yverdon':
                urljoin(reverse('api.stations', request=request), '?lat=46.78&lon=6.63&limit=3')
        },
        {
            'Geo search 20 km around Yverdon':
                urljoin(reverse('api.stations', request=request), '?lat=46.78&lon=6.63&distance=20000')
        },
        {
            'Text search':
                urljoin(reverse('api.stations', request=request), '?word=sommet')
        },
        {
            'Mauborget':
                reverse('api.station', ['jdc-1001'], request=request)
        },
        {
            'Historic Mauborget (1 hour)':
                urljoin(reverse('api.historic', ['jdc-1001'], request=request), '?duration=3600')
        },
    ]})


@api_view(['GET'])
def stations(request):
    search = request.QUERY_PARAMS.get('search')
    latitude = request.QUERY_PARAMS.get('lat')
    longitude = request.QUERY_PARAMS.get('lon')
    distance = request.QUERY_PARAMS.get('distance')
    word = request.QUERY_PARAMS.get('word')
    language = request.QUERY_PARAMS.get('language', 'fr')
    limit = int(request.QUERY_PARAMS.get('limit', 10))

    if not (search or latitude or longitude or distance or word):
        return Response(list(mongo_db.stations.find().limit(limit)))

    elif search and not (latitude or longitude or distance or word):
        regexp_query = diacritics.create_regexp(diacritics.normalize(search))
        return Response(list(mongo_db.stations.find({
            '$or': [{'name': {'$regex': regexp_query, '$options': 'i'}},
                    {'short': {'$regex': regexp_query, '$options': 'i'}},
                    {'tags': search}]
        }).limit(limit)))

    elif latitude and longitude and not (search or word):
        if distance:
            geo_search = {'loc': {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [float(latitude), float(longitude)]
                    },
                    '$maxDistance': int(distance)
                }
            }}
        else:
            geo_search = {'loc': {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [float(latitude), float(longitude)]
                    }
                }
            }}
        return Response(list(mongo_db.stations.find(geo_search).limit(limit)))

    elif word and not (search or latitude or longitude or distance):
        return Response(list(mongo_db.stations.find({'$text': {'$search': word, '$language': language}}).limit(limit)))

    else:
        raise ParseError(u"Invalid query parameters")


@api_view(['GET'])
def station(request, id):
    station = mongo_db.stations.find_one(id)
    if station:
        return Response(station)
    else:
        return Response({'detail': "No station with id '%s'" % id}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def historic(request, id):
    duration = int(request.QUERY_PARAMS.get('duration', 3600))

    if duration > 7 * 24 * 3600:
        raise ParseError(u"Duration > 7 days")

    if id in mongo_db.collection_names():
        station = mongo_db.stations.find_one(id)
        if not station or not 'last' in station:
            return Response({'detail': "No station with id '%s'" % id}, status=status.HTTP_404_NOT_FOUND)
        last_time = station['last']['_id']
        start_time = last_time - duration;
        return Response(list(mongo_db[id].find({'_id': {'$gte': start_time}}).sort('_id', -1)))
    else:
        return Response({'detail': "No historic data for id '%s'" % id}, status=status.HTTP_404_NOT_FOUND)


mongo_url = os.environ['WINDMOBILE_MONGO_URL']
uri = uri_parser.parse_uri(mongo_url)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]