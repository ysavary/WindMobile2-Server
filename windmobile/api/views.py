# coding=utf-8
import logging

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from pymongo import MongoClient, uri_parser, ASCENDING
from pymongo.errors import OperationFailure
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import diacritics
from .authentication import JWTAuthentication, IsJWTAuthenticated

log = logging.getLogger(__name__)


class Stations(APIView):
    """
    Search for stations

    Returns Array of [JSON](/api/2/stations/json-doc)

    Examples:

    - Get 5 stations from jdc.ch: [/api/2/stations/?limit=5&provider=jdc](/api/2/stations/?limit=5&provider=jdc)
    - Search (ignore accents): [/api/2/stations/?search=dole](/api/2/stations/?search=dole)
    - Search for 3 stations around Yverdon: [/api/2/stations/?near-lat=46.78&near-lon=6.63&limit=3](/api/2/stations/?near-lat=46.78&near-lon=6.63&limit=3)
    - Search 20 km around Yverdon: [/api/2/stations/?near-lat=46.78&near-lon=6.63&near-distance=20000](/api/2/stations/?near-lat=46.78&near-lon=6.63&near-distance=20000)
    - Return jdc-1001 and jdc-1002: [/api/2/stations/?ids=jdc-1001&ids=jdc-1002](/api/2/stations/?ids=jdc-1001&ids=jdc-1002)
    """

    def get(self, request):
        """
        ---
        parameters:
            - name: limit
              description: "Nb stations to return (default=20)"
              type: integer
              defaultValue: 20
              paramType: query
            - name: provider
              description: "Returns only stations of the given provider"
              type: string
              paramType: query
            - name: search
              description: "String to search (ignoring accent)"
              type: string
              paramType: query
            - name: near-lat
              description: "Geo search near: latitude ie 46.78"
              type: float
              paramType: query
            - name: near-lon
              description: "Geo search near: longitude ie 6.63"
              type: float
              paramType: query
            - name: near-distance
              description: "Geo search near: distance from lat,lon [meters]"
              type: integer
              paramType: query
            - name: within-pt1-lat
              description: "Geo search within rectangle: pt1 latitude"
              type: float
              paramType: query
            - name: within-pt1-lon
              description: "Geo search within rectangle: pt1 longitude"
              type: float
              paramType: query
            - name: within-pt2-lat
              description: "Geo search within rectangle: pt2 latitude"
              type: float
              paramType: query
            - name: within-pt2-lon
              description: "Geo search within rectangle: pt2 longitude"
              type: float
              paramType: query
            - name: ids
              description: "Returns stations by ids"
              type: string
              allowMultiple: true
            - name: keys
              description: "List of keys to return"
              type: string
              allowMultiple: true
              paramType: query
        """
        limit = int(request.query_params.get('limit', 20))
        provider = request.query_params.get('provider')
        search = request.query_params.get('search')
        near_latitude = request.query_params.get('near-lat')
        near_longitude = request.query_params.get('near-lon')
        near_distance = request.query_params.get('near-distance')
        within_pt1_latitude = request.query_params.get('within-pt1-lat')
        within_pt1_longitude = request.query_params.get('within-pt1-lon')
        within_pt2_latitude = request.query_params.get('within-pt2-lat')
        within_pt2_longitude = request.query_params.get('within-pt2-lon')
        ids = request.query_params.getlist('ids', None)

        projections = request.query_params.getlist('keys', None)
        if projections:
            projection_dict = {}
            for key in projections:
                projection_dict[key] = 1
        else:
            projection_dict = None

        query = {'status': {'$ne': 'hidden'}}

        if provider:
            query['pv-code'] = provider

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
            try:
                # $near results are already sorted: return now
                return Response(list(mongo_db.stations.find(query, projection_dict).limit(limit)))
            except OperationFailure as e:
                raise ParseError(e.details)

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

            try:
                density_search(
                    float(within_pt1_longitude),
                    float(within_pt1_latitude),
                    float(within_pt2_longitude),
                    float(within_pt2_latitude))
                return Response(result)
            except OperationFailure as e:
                raise ParseError(e.details)

        if ids:
            query['_id'] = {'$in': ids}

        try:
            return Response(list(mongo_db.stations.find(query, projection_dict).sort('short', ASCENDING).limit(limit)))
        except OperationFailure as e:
            raise ParseError(e.details)


class Station(APIView):
    """
    Get a station

    Returns [JSON](/api/2/stations/json-doc)

    Example:

    - Mauborget: [/api/2/stations/jdc-1001](/api/2/stations/jdc-1001)
    """

    def get(self, request, station_id):
        """
        ---
        parameters:
            - name: station_id
              description: "The station ID to request"
              type: string
              required: true
              paramType: path
        """
        station = mongo_db.stations.find_one(station_id)
        if not station:
            return Response({'detail': "No station with id '{0}'".format(station_id)}, status=status.HTTP_404_NOT_FOUND)

        return Response(station)


class StationJsonDoc(APIView):
    """
    [Station JSON documentation](/api/2/stations/json-doc)
    """

    def get(self, request):
        return Response({
            "_id": "[string] unique ID {providerCode}-{providerId} (jdc-1010)",
            "pv-code": "[string] provider code (jdc)",
            "pv-name": "[string] provider name (jdc.ch)",

            "short": "[string] short name",
            "name": "[string] name",
            "alt": "[integer] altitude [m]",
            "peak": "[boolean] is the station on a peak",

            "status": "green|orange|red",
            "tz": "[string]: (Europe/Zurich)",

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


class StationHistoric(APIView):
    """
    Get historic data for a station since a duration

    Returns Array of [JSON](/api/2/stations/historic/json-doc)

    Example:

    - Historic Mauborget (1 hour): [/api/2/stations/jdc-1001/historic/?duration=3600](/api/2/stations/jdc-1001/historic/?duration=3600)

    """

    def get(self, request, station_id):
        """
        ---
        parameters:
            - name: station_id
              description: "The station ID to request"
              type: string
              required: true
              paramType: path
            - name: duration
              description: "Historic duration"
              type: integer
              defaultValue: 3600
              paramType: query
            - name: keys
              description: "List of keys to return"
              type: string
              allowMultiple: true
              paramType: query
        """
        duration = int(request.query_params.get('duration', 3600))

        projections = request.query_params.getlist('keys', None)
        if projections:
            projection_dict = {}
            for key in projections:
                projection_dict[key] = 1
        else:
            projection_dict = None

        if duration > 7 * 24 * 3600:
            raise ParseError("Duration > 7 days")

        station = mongo_db.stations.find_one(station_id)
        if not station:
            return Response({'detail': "No station with id '{0}'".format(station_id)}, status=status.HTTP_404_NOT_FOUND)

        if 'last' not in station or station_id not in mongo_db.collection_names():
            return Response({'detail': "No historic data for station id '{0}'".format(station_id)},
                            status=status.HTTP_404_NOT_FOUND)
        last_time = station['last']['_id']
        start_time = last_time - duration
        nb_data = mongo_db[station_id].find({'_id': {'$gte': start_time}}).count() + 1
        return Response(list(mongo_db[station_id].find({}, projection_dict, sort=(('_id', -1),)).limit(nb_data)))


class StationHistoricJsonDoc(APIView):
    """
    [Station historic JSON documentation](/api/2/stations/historic/json-doc)
    """

    def get(self, request):
        return Response({
            "_id": "[integer] unix time",
            "w-dir": "[integer] wind direction [°](0-359)",
            "w-avg": "[integer] wind speed [km/h]",
            "w-max": "[integer] wind speed max [km/h]",
            "temp": "[integer] temperature [°C]",
            "hum": "[integer] air humidity [%rH]",
            "rain": "[integer] rain [l/m²]",
            "pres": "[integer] air pressure [hPa]"
        })


class AuthenticationLogin(APIView):
    """
    Login into API with a One Time Token or a Django username/password
    """

    def post(self, request):
        ott = request.data.get('ott')
        username = request.data.get('username')
        password = request.data.get('password')

        if ott:
            ott_doc = mongo_db.login_ott.find_one_and_delete({'_id': ott})
            if not ott_doc:
                log.warn("Unable to find One Time Token")
                raise AuthenticationFailed()
            username = ott_doc['username']
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                log.warn("Unable to get One Time Token's user")
                raise AuthenticationFailed()
            token = jwt.encode({'username': username}, settings.SECRET_KEY)
            return Response({'token': token.decode('utf-8')})
        elif username and password:
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    token = jwt.encode({'username': username}, settings.SECRET_KEY)
                    return Response({'token': token.decode('utf-8')})
                else:
                    log.warn("The password is valid, but the account has been disabled")
                    raise AuthenticationFailed()
            else:
                log.warn("The username and password were incorrect")
                raise AuthenticationFailed()
        else:
            raise NotAuthenticated()


class UserProfile(APIView):
    """
    Get profile of authenticated user
    """
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsJWTAuthenticated,)

    def get(self, request):
        profile = mongo_db.users.find_one(request.user)
        if profile:
            return Response(profile)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)


class UserProfileFavorite(APIView):
    """
    Manage favorites stations list
    """
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsJWTAuthenticated,)

    def post(self, request):
        station_id = request.data['station_id']
        mongo_db.users.update_one({'_id': request.user},
                                  {'$addToSet': {'favorites': station_id}},
                                  upsert=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        station_id = request.data['station_id']
        mongo_db.users.update_one({'_id': request.user},
                                  {'$pull': {'favorites': station_id}},
                                  upsert=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


uri = uri_parser.parse_uri(settings.MONGODB_URL)
mongo_client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = mongo_client[uri['database']]
