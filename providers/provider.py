import logging
import logging.config
import logging.handlers
import math
from os import path
from random import randint

import arrow
import dateutil
import redis
import requests
import yaml
from pint import UnitRegistry
from pymongo import uri_parser, MongoClient, GEOSPHERE, ASCENDING
from pymongo.errors import CollectionInvalid
from raven import Client as RavenClient

from settings import *

ureg = UnitRegistry()
Q_ = ureg.Quantity


def get_logger(name):
    if WINDMOBILE_LOG_DIR:
        with open(path.join(path.dirname(path.abspath(__file__)), 'logging_file.yml')) as f:
            dict = yaml.load(f)
            dict['handlers']['file']['filename'] = path.join(path.expanduser(WINDMOBILE_LOG_DIR), name + '.log')
            logging.config.dictConfig(dict)
    else:
        with open(path.join(path.dirname(path.abspath(__file__)), 'logging_console.yml')) as f:
            logging.config.dictConfig(yaml.load(f))

    logger = logging.getLogger(name)
    return logger


class ProviderException(Exception):
    pass


class UsageLimitException(ProviderException):
    pass


class Status:
    HIDDEN = 'hidden'
    RED = 'red'
    ORANGE = 'orange'
    GREEN = 'green'


def to_int(value, mandatory=False):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        if mandatory:
            return 0
        return None


def to_float(value, ndigits=1, mandatory=False):
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        if mandatory:
            return 0.0
        return None


def to_bool(value):
    return str(value).lower() in ['true', 'yes']


def to_wind_direction(value):
    if isinstance(value, ureg.Quantity):
        return to_int(value.to(ureg.degree).magnitude, mandatory=True)
    else:
        return to_int(value, mandatory=True)


def to_wind_speed(value):
    if isinstance(value, ureg.Quantity):
        return to_float(value.to(ureg.kilometer / ureg.hour).magnitude, 1, mandatory=True)
    else:
        return to_float(value, 1, mandatory=True)


def to_temperature(value):
    if isinstance(value, ureg.Quantity):
        return to_float(value.to(ureg.degC).magnitude, 1)
    else:
        return to_float(value, 1)


def to_pressure(value):
    if isinstance(value, ureg.Quantity):
        return to_int(value.to(ureg.Pa * 100).magnitude)
    else:
        return to_int(value)


class Provider(object):
    connect_timeout = 7
    read_timeout = 30

    @property
    def usage_limit_cache_duration(self):
        return (12 + randint(-2, 2)) * 3600

    @property
    def location_cache_duration(self):
        return (20 + randint(-2, 2)) * 24 * 3600

    def __init__(self):
        uri = uri_parser.parse_uri(MONGODB_URL)
        client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
        self.mongo_db = client[uri['database']]
        self.__stations_collection = self.mongo_db.stations
        self.__stations_collection.create_index([('loc', GEOSPHERE), ('status', ASCENDING), ('pv-code', ASCENDING),
                                                 ('short', ASCENDING), ('name', ASCENDING)])
        self.redis = redis.StrictRedis(decode_responses=True)
        self.google_api_key = GOOGLE_API_KEY
        self.raven_client = RavenClient(SENTRY_URL)
        self.raven_client.tags_context({'provider': self.provider_name})

    def stations_collection(self):
        return self.__stations_collection

    def measures_collection(self, station_id):
        try:
            return self.mongo_db.create_collection(station_id, **{'capped': True, 'size': 500000, 'max': 5000})
        except CollectionInvalid:
            return self.mongo_db[station_id]

    def get_station_id(self, id):
        if id is None:
            raise ProviderException('Station id is none!')
        return self.provider_code + "-" + str(id)

    def __create_station(self, provider_id, short_name, name, latitude, longitude, altitude, is_peak, status, tz,
                         url=None):

        if any((not short_name, not name, altitude is None, latitude is None, longitude is None, not status, not tz)):
            raise ProviderException("A mandatory value is none!")

        station = {
            'pv-id': provider_id,
            'pv-code': self.provider_code,
            'pv-name': self.provider_name,
            'url': url or self.provider_url,
            'short': short_name,
            'name': name,
            'alt': to_int(altitude),
            'peak': to_bool(is_peak),
            'loc': {
                'type': 'Point',
                'coordinates': [
                    to_float(longitude, 6),
                    to_float(latitude, 6)
                ]
            },
            'status': status,
            'tz': tz,
            'seen': arrow.utcnow().timestamp
        }
        return station

    def add_redis_key(self, key, values, cache_duration):
        pipe = self.redis.pipeline()
        pipe.hmset(key, values)
        pipe.expire(key, cache_duration)
        pipe.execute()

    def compute_elevation(self, lat, lon):
        radius = 500
        nb = 6
        path = "{lat},{lon}|".format(lat=lat, lon=lon)
        for k in range(nb):
            angle = math.pi * 2 * k / nb
            dx = radius * math.cos(angle)
            dy = radius * math.sin(angle)
            path += "{lat},{lon}".format(
                lat=str(lat + (180 / math.pi) * (dy / 6378137)),
                lon=str(lon + (180 / math.pi) * (dx / 6378137) / math.cos(lat * math.pi / 180)))
            if k < nb - 1:
                path += '|'

        result = requests.get(
            "https://maps.googleapis.com/maps/api/elevation/json?locations={path}&key={key}"
            .format(path=path, key=self.google_api_key),
            timeout=(self.connect_timeout, self.read_timeout)).json()
        if result['status'] == 'OVER_QUERY_LIMIT':
            raise UsageLimitException("Google Elevation API: OVER_QUERY_LIMIT")
        elif result['status'] == 'INVALID_REQUEST':
            raise ProviderException("Google Elevation API: INVALID_REQUEST {message}"
                                    .format(message=result.get('error_message', '')))
        elif result['status'] == 'ZERO_RESULTS':
            raise ProviderException("Google Elevation API: ZERO_RESULTS {message}"
                                    .format(message=result.get('error_message', '')))

        elevation = float(result['results'][0]['elevation'])
        is_peak = False
        for point in result['results'][1:]:
            try:
                glide_ratio = radius / (elevation - float(point['elevation']))
            except ZeroDivisionError:
                glide_ratio = float('Infinity')
            if 0 < glide_ratio < 6:
                is_peak = True
                break
        return elevation, is_peak

    def save_station(self, provider_id, short_name, name, latitude, longitude, status, altitude=None, tz=None, url=None,
                     default_name=None):

        _id = self.get_station_id(provider_id)
        lat = to_float(latitude, 6)
        lon = to_float(longitude, 6)

        address_key = "address/{lat},{lon}".format(lat=lat, lon=lon)
        if (not short_name or not name) and not self.redis.exists(address_key):
            try:
                results = requests.get(
                    "https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}"
                    "&result_type=colloquial_area|locality|natural_feature|point_of_interest|neighborhood&key={key}"
                    .format(lat=lat, lon=lon, key=self.google_api_key),
                    timeout=(self.connect_timeout, self.read_timeout)).json()
                if results['status'] == 'OVER_QUERY_LIMIT':
                    raise UsageLimitException("Google Geocoding API: OVER_QUERY_LIMIT")
                elif results['status'] == 'INVALID_REQUEST':
                    raise ProviderException("Google Geocoding API: INVALID_REQUEST {message}"
                                            .format(message=results.get('error_message', '')))
                elif results['status'] == 'ZERO_RESULTS':
                    raise ProviderException("Google Geocoding API: ZERO_RESULTS {message}"
                                            .format(message=results.get('error_message', '')))
                address_short_name = None
                address_long_name = None
                for result in results['results']:
                    for component in result['address_components']:
                        if 'postal_code' not in component['types']:
                            address_short_name = component['short_name']
                            address_long_name = component['long_name']
                            break
                if not address_short_name or not address_long_name:
                    raise ProviderException("Google Geocoding API: No valid address name found")
                self.add_redis_key(address_key, {
                    '_id': _id,
                    'short': address_short_name,
                    'name': address_long_name
                }, self.location_cache_duration)
            except TimeoutError as e:
                raise e
            except UsageLimitException as e:
                self.add_redis_key(address_key, {
                    '_id': _id,
                    'error': repr(e)
                }, self.usage_limit_cache_duration)
            except Exception as e:
                if not isinstance(e, ProviderException):
                    self.raven_client.captureException()
                self.add_redis_key(address_key, {
                    '_id': _id,
                    'error': repr(e)
                }, self.location_cache_duration)

        address = name or short_name
        geolocation_key = "geolocation/{address}".format(address=address)
        if (lat is None and lon is None) or (lat == 0 and lon == 0):
            if not self.redis.exists(geolocation_key):
                try:
                    results = requests.get(
                        "https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={key}".format(
                            address=address, key=self.google_api_key),
                        timeout=(self.connect_timeout, self.read_timeout)).json()
                    if results['status'] == 'OVER_QUERY_LIMIT':
                        raise UsageLimitException("Google Geocoding API: OVER_QUERY_LIMIT")
                    elif results['status'] == 'INVALID_REQUEST':
                        raise ProviderException("Google Geocoding API: INVALID_REQUEST {message}".format(
                            message=results.get('error_message', '')))
                    elif results['status'] == 'ZERO_RESULTS':
                        raise ProviderException("Google Geocoding API: ZERO_RESULTS {message}".format(
                            message=results.get('error_message', '')))
                    lat = None
                    lon = None
                    address_long_name = None
                    for result in results['results']:
                        if result.get('geometry', {}).get('location'):
                            lat = result['geometry']['location']['lat']
                            lon = result['geometry']['location']['lng']
                            for component in result['address_components']:
                                if 'postal_code' not in component['types']:
                                    address_long_name = component['long_name']
                                    break
                            break
                    for result in results['results']:
                        if 'airport' in result['types'] and result.get('geometry', {}).get('location'):
                            for component in result['address_components']:
                                if 'postal_code' not in component['types']:
                                    address_long_name = component['long_name']
                                    break
                            break
                    if not lat or not lon or not address_long_name:
                        raise ProviderException(
                            "Google Geocoding API: No valid geolocation found for '{address}'".format(
                                address=address))
                    self.add_redis_key(geolocation_key, {
                        '_id': _id,
                        'lat': lat,
                        'lon': lon,
                        'name': address_long_name
                    }, self.location_cache_duration)
                except TimeoutError as e:
                    raise e
                except UsageLimitException as e:
                    self.add_redis_key(geolocation_key, {
                        '_id': _id,
                        'error': repr(e)
                    }, self.usage_limit_cache_duration)
                except Exception as e:
                    if not isinstance(e, ProviderException):
                        self.raven_client.captureException()
                    self.add_redis_key(geolocation_key, {
                        '_id': _id,
                        'error': repr(e)
                    }, self.location_cache_duration)
            if self.redis.exists(geolocation_key):
                if self.redis.hexists(geolocation_key, 'error'):
                    raise ProviderException("Unable to determine station geolocation: {message}".format(
                        message=self.redis.hget(geolocation_key, 'error')))
                lat = to_float(self.redis.hget(geolocation_key, 'lat'), 6)
                lon = to_float(self.redis.hget(geolocation_key, 'lon'), 6)
                if not name:
                    name = self.redis.hget(geolocation_key, 'name')

        alt_key = "alt/{lat},{lon}".format(lat=lat, lon=lon)
        if not self.redis.exists(alt_key):
            try:
                elevation, is_peak = self.compute_elevation(lat, lon)
                self.add_redis_key(alt_key, {
                    'alt': elevation,
                    'is_peak': is_peak
                }, self.location_cache_duration)
            except TimeoutError as e:
                raise e
            except UsageLimitException as e:
                self.add_redis_key(alt_key, {
                    '_id': _id,
                    'error': repr(e)
                }, self.usage_limit_cache_duration)
            except Exception as e:
                if not isinstance(e, ProviderException):
                    self.raven_client.captureException()
                self.add_redis_key(alt_key, {
                    '_id': _id,
                    'error': repr(e)
                }, self.location_cache_duration)

        tz_key = "tz/{lat},{lon}".format(lat=lat, lon=lon)
        if not tz and not self.redis.exists(tz_key):
            try:
                result = requests.get(
                    "https://maps.googleapis.com/maps/api/timezone/json?location={lat},{lon}"
                    "&timestamp={utc}&key={key}"
                    .format(lat=lat, lon=lon, utc=arrow.utcnow().timestamp, key=self.google_api_key),
                    timeout=(self.connect_timeout, self.read_timeout)).json()
                if result['status'] == 'OVER_QUERY_LIMIT':
                    raise UsageLimitException("Google Time Zone API: OVER_QUERY_LIMIT")
                elif result['status'] == 'INVALID_REQUEST':
                    raise ProviderException("Google Time Zone API: INVALID_REQUEST {message}".format(
                        message=result.get('error_message', '')))
                elif result['status'] == 'ZERO_RESULTS':
                    raise ProviderException("Google Time Zone API: ZERO_RESULTS {message}".format(
                        message=result.get('error_message', '')))
                tz = result['timeZoneId']
                dateutil.tz.gettz(tz)
                self.add_redis_key(tz_key, {
                    '_id': _id,
                    'tz': tz
                }, self.location_cache_duration)
            except TimeoutError as e:
                raise e
            except UsageLimitException as e:
                self.add_redis_key(tz_key, {
                    '_id': _id,
                    'error': repr(e)
                }, self.usage_limit_cache_duration)
            except Exception as e:
                if not isinstance(e, ProviderException):
                    self.raven_client.captureException()
                self.add_redis_key(tz_key, {
                    '_id': _id,
                    'error': repr(e)
                }, self.location_cache_duration)

        if not short_name:
            if self.redis.hexists(address_key, 'error'):
                if default_name:
                    short_name = default_name
                else:
                    raise ProviderException("Unable to determine station 'short': {message}".format(
                        message=self.redis.hget(address_key, 'error')))
            else:
                short_name = self.redis.hget(address_key, 'short')

        if not name:
            if self.redis.hexists(address_key, 'error'):
                if default_name:
                    name = default_name
                else:
                    raise ProviderException("Unable to determine station 'name': {message}".format(
                        message=self.redis.hget(address_key, 'error')))
            else:
                name = self.redis.hget(address_key, 'name')

        if not altitude:
            if self.redis.hexists(alt_key, 'error'):
                raise ProviderException("Unable to determine station 'alt': {message}".format(
                    message=self.redis.hget(alt_key, 'error')))
            altitude = self.redis.hget(alt_key, 'alt')

        if self.redis.hexists(alt_key, 'error') == 'error':
            raise ProviderException("Unable to determine station 'peak': {message}".format(
                    message=self.redis.hget(alt_key, 'error')))
        is_peak = self.redis.hget(alt_key, 'is_peak')

        if not tz:
            if self.redis.hexists(tz_key, 'error'):
                raise ProviderException("Unable to determine station 'tz': {message}".format(
                    message=self.redis.hget(tz_key, 'error')))
            tz = self.redis.hget(tz_key, 'tz')

        station = self.__create_station(provider_id, short_name, name, lat, lon, altitude, is_peak, status, tz, url)
        self.stations_collection().update({'_id': _id}, {'$set': station}, upsert=True)
        station['_id'] = _id
        return station

    def create_measure(self, _id, wind_direction, wind_average, wind_maximum,
                       temperature=None, humidity=None, pressure=None, luminosity=None, rain=None):

        if all((wind_direction is None, wind_average is None, wind_maximum is None)):
            raise ProviderException("All mandatory values are null!")

        # Mandatory keys: json 'null' if not present
        measure = {
            '_id': _id,
            'w-dir': to_wind_direction(wind_direction),
            'w-avg': to_wind_speed(wind_average),
            'w-max': to_wind_speed(wind_maximum)
        }

        # Optional keys
        if temperature is not None:
            measure['temp'] = to_temperature(temperature)
        if humidity is not None:
            measure['hum'] = to_float(humidity, 1)
        if pressure is not None:
            measure['pres'] = to_pressure(pressure)
        if luminosity is not None:
            measure['lum'] = to_int(luminosity)
        if rain is not None:
            measure['rain'] = to_float(rain, 1)

        measure['time'] = arrow.now().timestamp
        return measure

    def has_measure(self, measure_collection, key):
        return measure_collection.find({'_id': key}).count() > 0

    def insert_new_measures(self, measure_collection, station, new_measures, logger):
        if len(new_measures) > 0:
            measure_collection.insert(new_measures)

            end_date = arrow.Arrow.fromtimestamp(new_measures[-1]['_id'], dateutil.tz.gettz(station['tz']))
            logger.info(
                "--> {end_date} ({end_date_local}), {short}/{name} ({id}): {nb} values inserted".format(
                    end_date=end_date.format('YY-MM-DD HH:mm:ssZZ'),
                    end_date_local=end_date.to('local').format('YY-MM-DD HH:mm:ssZZ'),
                    short=station['short'],
                    name=station['name'],
                    id=station['_id'],
                    nb=str(len(new_measures))))

            self.__add_last_measure(measure_collection, station['_id'])

    def __add_last_measure(self, measure_collection, station_id):
        last_measure = measure_collection.find_one({'$query': {}, '$orderby': {'_id': -1}})
        if last_measure:
            self.stations_collection().update({'_id': station_id}, {'$set': {'last': last_measure}})
