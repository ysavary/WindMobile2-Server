# coding=utf-8
import os

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from pymongo import MongoClient, uri_parser
from pymongo.errors import OperationFailure

from windmobile.api import diacritics


@api_view(['GET'])
def stations(request):
    """
    Search stations queries

    Examples:
    - Get 5 stations from jdc.ch: <a href=/api/2/stations/?limit=5&provider=jdc.ch>/api/2/stations/?limit=5&provider=jdc.ch</a>
    - Search (ignore accents): <a href=/api/2/stations/?search=dole>/api/2/stations/?search=dole</a>
    - Search for 3 stations around Yverdon: <a href=/api/2/stations/?lat=46.78&lon=6.63&limit=3>/api/2/stations/?lat=46.78&lon=6.63&limit=3</a>
    - Search 20 km around Yverdon: <a href=/api/2/stations/?lat=46.78&lon=6.63&distance=20000>/api/2/stations/?lat=46.78&lon=6.63&distance=20000</a>
    - Text search: <a href=/api/2/stations/?word=sommet>/api/2/stations/?word=sommet</a>

    Query parameters:
    limit     -- Nb stations to return (default=20)
    provider  -- Return only stations of the given provider
    search    -- String to search (ignoring accent)
    lat       -- Geo search: latitude ie 46.78
    lon       -- Geo search: longitude ie 6.63
    distance  -- Geo search: distance from lat, lon
    word      -- Full text search
    language  -- Language of the query (default 'fr')
    """
    limit = int(request.QUERY_PARAMS.get('limit', 20))
    provider = request.QUERY_PARAMS.get('provider')
    search = request.QUERY_PARAMS.get('search')
    latitude = request.QUERY_PARAMS.get('lat')
    longitude = request.QUERY_PARAMS.get('lon')
    distance = request.QUERY_PARAMS.get('distance')
    word = request.QUERY_PARAMS.get('word')
    language = request.QUERY_PARAMS.get('language', 'fr')

    query = {'status': {'$ne': 'hidden'}}

    if provider:
        query['prov'] = provider

    if search:
        regexp_query = diacritics.create_regexp(diacritics.normalize(search))
        query['$or'] = [{'name': {'$regex': regexp_query, '$options': 'i'}},
                        {'short': {'$regex': regexp_query, '$options': 'i'}},
                        {'tags': search}]

    if latitude and longitude:
        if distance:
            query['loc'] = {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [float(longitude), float(latitude)]
                    },
                    '$maxDistance': int(distance)
                }
            }
        else:
            query['loc'] = {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [float(longitude), float(latitude)]
                    }
                }
            }

    if word:
        query['$text'] = {'$search': word, '$language': language}

    try:
        return Response(list(mongo_db.stations.find(query).limit(limit)))
    except OperationFailure as e:
        raise ParseError(e.details)

@api_view(['GET'])
def station_json_doc(request):
    """
    JSON station data documentation

    """
    return Response({
        "_id": "[string] unique ID {providerCode}-{providerId} (jdc-1010)",
        "prov": "[string] provider name (jdc.ch)",

        "short": "[string] short name",
        "name": "[string] name",
        "alt": "[integer] altitude [m]",

        "status": "green|orange|red",
        "timezone": "[string]: (+01:00)",

        "loc": {
            'type': 'Point',
            'coordinates': "[ [float] longitude, [float] latitude ]"
        },
        "tags": "[array of string] tags",
        "cat": "[string] category",
        "seen": "[integer] last time updated (unix time)",

        "last": {
            "_id": "[integer] unix time",
            "w-dir": "[integer] wind direction [°](0-359)",
            "w-avg": "[integer] wind speed [km/h]",
            "w-max": "[integer] wind speed max [km/h]",
            "temp": "[integer] temperature [°C]",
            "hum": "[integer] air humidity [%rH]",
            "rain": "[integer] rain [l/m²]",
            "pres": "[integer] air pressure [hPa]"
        }
    })


@api_view(['GET'])
def station(request, station_id):
    """
    Get station data

    <a href=/api/2/stations/station_json_doc>JSON station data documentation</a>

    Example:
    - Mauborget: <a href=/api/2/stations/jdc-1001>/api/2/stations/jdc-1001</a>

    """
    station = mongo_db.stations.find_one(station_id)
    if station:
        return Response(station)
    else:
        return Response({'detail': "No station with id '%s'" % station_id}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def station_historic(request, station_id):
    """
    Get data history of a station since at least duration

    Example:
    - Historic Mauborget (1 hour): <a href=/api/2/stations/jdc-1001/historic/?duration=3600>/api/2/stations/jdc-1001/historic/?duration=3600</a>

    """
    duration = int(request.QUERY_PARAMS.get('duration', 3600))

    if duration > 7 * 24 * 3600:
        raise ParseError(u"Duration > 7 days")

    if station_id in mongo_db.collection_names():
        station = mongo_db.stations.find_one(station_id)
        if not station or not 'last' in station:
            return Response({'detail': "No station with id '%s'" % station_id}, status=status.HTTP_404_NOT_FOUND)
        last_time = station['last']['_id']
        start_time = last_time - duration
        nb_data = mongo_db[station_id].find({'_id': {'$gte': start_time}}).count() + 1
        return Response(list(mongo_db[station_id].find({}, sort=(('_id', -1),)).limit(nb_data)))
    else:
        return Response({'detail': "No historic data for id '%s'" % station_id}, status=status.HTTP_404_NOT_FOUND)


mongo_url = os.environ['WINDMOBILE_MONGO_URL']
uri = uri_parser.parse_uri(mongo_url)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]