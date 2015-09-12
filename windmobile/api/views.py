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

    Query parameters:
    limit          -- Nb stations to return (default=20)
    provider       -- Return only stations of the given provider
    search         -- String to search (ignoring accent)
    near-lat       -- Geo search near: latitude ie 46.78
    near-lon       -- Geo search near: longitude ie 6.63
    near-distance  -- Geo search near: distance from lat, lon
    within-pt1-lat -- Geo search within rectangle: pt1 latitude
    within-pt1-lon -- Geo search within rectangle: pt1 longitude
    within-pt2-lat -- Geo search within rectangle: pt2 latitude
    within-pt2-lon -- Geo search within rectangle: pt2 longitude
    word           -- Full text search
    language       -- Language of the query (default 'fr')
    """
    limit = int(request.QUERY_PARAMS.get('limit', 20))
    provider = request.QUERY_PARAMS.get('provider')
    search = request.QUERY_PARAMS.get('search')
    near_latitude = request.QUERY_PARAMS.get('near-lat')
    near_longitude = request.QUERY_PARAMS.get('near-lon')
    near_distance = request.QUERY_PARAMS.get('near-distance')
    within_pt1_latitude = request.QUERY_PARAMS.get('within-pt1-lat')
    within_pt1_longitude = request.QUERY_PARAMS.get('within-pt1-lon')
    within_pt2_latitude = request.QUERY_PARAMS.get('within-pt2-lat')
    within_pt2_longitude = request.QUERY_PARAMS.get('within-pt2-lon')
    word = request.QUERY_PARAMS.get('word')
    language = request.QUERY_PARAMS.get('language', 'fr')

    projections = request.QUERY_PARAMS.getlist('proj', None)
    if projections:
        projection_dict = {}
        for key in projections:
            projection_dict[key] = 1
    else:
        projection_dict = None

    query = {'status': {'$ne': 'hidden'}}

    if provider:
        query['prov'] = provider

    if search:
        regexp_query = diacritics.create_regexp(diacritics.normalize(search))
        query['$or'] = [{'name': {'$regex': regexp_query, '$options': 'i'}},
                        {'short': {'$regex': regexp_query, '$options': 'i'}}]

    if near_latitude and near_longitude:
        if near_distance:
            query['loc'] = {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [float(near_longitude), float(near_latitude)]
                    },
                    '$maxDistance': int(near_distance)
                }
            }
        else:
            query['loc'] = {
                '$near': {
                    '$geometry': {
                        'type': 'Point',
                        'coordinates': [float(near_longitude), float(near_latitude)]
                    }
                }
            }

    if within_pt1_latitude and within_pt1_longitude and within_pt2_latitude and within_pt2_longitude:
        result = []

        def density_search(x1, y1, x2, y2, level=1):
            sub_limit = limit // (pow(3, level - 1))
            query['loc'] = {
                '$geoWithin': {
                    '$geometry': {
                        'type': 'Polygon',
                        'coordinates': [[(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]],
                        # Resolves "Big polygon" issue, requires mongodb 3.x
                        # http://docs.mongodb.org/manual/reference/operator/query/geometry/#op._S_geometry
                        'crs': {
                            'type': 'name',
                            'properties': {'name': 'urn:x-mongodb:crs:strictwinding:EPSG:4326'}
                        }
                    }
                }
            }
            cursor = mongo_db.stations.find(query, projection_dict)
            count = cursor.count()

            if count > 0:
                if sub_limit == 0:
                    result.extend(list(cursor.limit(1)))
                elif count <= sub_limit:
                    result.extend(list(cursor))
                else:
                    delta_x = (x2 - x1) / 2
                    delta_y = (y2 - y1) / 2

                    for i in range(0, 2):
                        i1 = x1 + i * delta_x
                        i2 = x1 + (i + 1) * delta_x
                        for j in range(0, 2):
                            j1 = y1 + j * delta_y
                            j2 = y1 + (j + 1) * delta_y
                            density_search(i1, j1, i2, j2, level + 1)

        density_search(
            float(within_pt1_longitude),
            float(within_pt1_latitude),
            float(within_pt2_longitude),
            float(within_pt2_latitude))
        return Response(result)

    if word:
        query['$text'] = {'$search': word, '$language': language}

    try:
        return Response(list(mongo_db.stations.find(query, projection_dict).limit(limit)))
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

    projections = request.QUERY_PARAMS.getlist('proj', None)
    if projections:
        projection_dict = {}
        for key in projections:
            projection_dict[key] = 1
    else:
        projection_dict = None

    if duration > 7 * 24 * 3600:
        raise ParseError("Duration > 7 days")

    if station_id in mongo_db.collection_names():
        station = mongo_db.stations.find_one(station_id)
        if not station or not 'last' in station:
            return Response({'detail': "No station with id '%s'" % station_id}, status=status.HTTP_404_NOT_FOUND)
        last_time = station['last']['_id']
        start_time = last_time - duration
        nb_data = mongo_db[station_id].find({'_id': {'$gte': start_time}}).count() + 1
        return Response(list(mongo_db[station_id].find({}, projection_dict, sort=(('_id', -1),)).limit(nb_data)))
    else:
        return Response({'detail': "No historic data for id '%s'" % station_id}, status=status.HTTP_404_NOT_FOUND)


mongo_url = os.environ['WINDMOBILE_MONGO_URL']
uri = uri_parser.parse_uri(mongo_url)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]