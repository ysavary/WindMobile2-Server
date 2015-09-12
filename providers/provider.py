import sys
import os
import logging
import logging.handlers
from pymongo import uri_parser, MongoClient, GEOSPHERE
from pymongo.errors import CollectionInvalid

# Modules
import requests
import arrow
import dateutil
import redis


class NoExceptionFormatter(logging.Formatter):
    def format(self, record):
        record.exc_text = ''  # ensure formatException gets called
        return super(NoExceptionFormatter, self).format(record)

    def formatException(self, record):
        return ''


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter('%(levelname)s [%(name)s]: %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    if 'WINDMOBILE_LOG_DIR' in os.environ:
        try:
            handler = logging.handlers.TimedRotatingFileHandler(
                os.path.join(os.environ['WINDMOBILE_LOG_DIR'], name + '.log'), when='midnight', backupCount=20)
            fmt = NoExceptionFormatter('%(asctime)s %(levelname)s [%(name)s]: %(message)s', '%Y-%m-%dT%H:%M:%S%z')
            handler.setFormatter(fmt)
            logger.addHandler(handler)

            handler = logging.handlers.RotatingFileHandler(
                os.path.join(os.environ['WINDMOBILE_LOG_DIR'], name + '.stacktraces.log'), maxBytes=50 * 10 ** 6)
            fmt = logging.Formatter('%(asctime)s %(levelname)s [%(name)s]: %(message)s', '%Y-%m-%dT%H:%M:%S%z')
            handler.setFormatter(fmt)
            logger.addHandler(handler)
        except IOError:
            logger.exception("Unable to create file logger")

    return logger


class ProviderException(Exception):
    pass


class Status:
    HIDDEN = 'hidden'
    RED = 'red'
    ORANGE = 'orange'
    GREEN = 'green'


def to_int(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def to_float(value, ndigits=1):
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


class Provider(object):
    connect_timeout = 7
    read_timeout = 30

    def __init__(self, mongo_url):
        uri = uri_parser.parse_uri(mongo_url)
        client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
        self.mongo_db = client[uri['database']]
        self.redis = redis.StrictRedis()

    def stations_collection(self):
        collection = self.mongo_db.stations
        collection.create_index('short')
        collection.create_index('name')
        collection.create_index([('loc', GEOSPHERE)])
        return collection

    def measures_collection(self, station_id):
        try:
            return self.mongo_db.create_collection(station_id, **{'capped': True, 'size': 500000, 'max': 5000})
        except CollectionInvalid:
            return self.mongo_db[station_id]

    def get_station_id(self, id):
        return self.provider_prefix + "-" + str(id)

    def __create_station(self, short_name, name, altitude, latitude, longitude, status, tz, url=None):

        if any((not short_name, not name, altitude is None, latitude is None, longitude is None, not status, not tz)):
            raise ProviderException("A mandatory value is null!")

        station = {'prov': self.provider_name,
                   'url': url or self.provider_url,
                   'short': short_name,
                   'name': name,
                   'alt': to_int(altitude),
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

    def save_station(self, _id, short_name, name, latitude, longitude, status, altitude=None, tz=None, url=None):
        try:
            if not altitude and not self.redis.get("elevation-api-{_id}".format(_id=_id)):
                result = requests.get(
                    "https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={key}"
                    .format(lat=to_float(latitude, 6),
                            lon=to_float(longitude, 6),
                            key=os.environ['GOOGLE_API_KEY']),
                    timeout=(self.connect_timeout, self.read_timeout))
                if result.json()['status'] == 'OVER_QUERY_LIMIT':
                    raise ProviderException('maps.googleapis.com/maps/api/elevation: usage limits exceeded')
                self.redis.setex("elevation-api-{_id}".format(_id=_id), 3600, 'ok')
                if result.json()['status'] == 'REQUEST_DENIED':
                    raise ProviderException('maps.googleapis.com/maps/api/elevation: request denied')
                altitude = to_int(result.json()['results'][0]['elevation'])

            if not tz and not self.redis.get("timezone-api-{_id}".format(_id=_id)):
                result = requests.get(
                    "https://maps.googleapis.com/maps/api/timezone/json?location={lat},{lon}&timestamp={utc}&key={key}"
                    .format(lat=to_float(latitude, 6),
                            lon=to_float(longitude, 6),
                            utc=arrow.utcnow().timestamp,
                            key=os.environ['GOOGLE_API_KEY']),
                    timeout=(self.connect_timeout, self.read_timeout))
                if result.json()['status'] == 'OVER_QUERY_LIMIT':
                    raise ProviderException('maps.googleapis.com/maps/api/timezone: usage limits exceeded')
                self.redis.setex("timezone-api-{_id}".format(_id=_id), 3600, 'ok')
                if result.json()['status'] == 'REQUEST_DENIED':
                    raise ProviderException('maps.googleapis.com/maps/api/elevation: request denied')
                tz = result.json()['timeZoneId']
                dateutil.tz.gettz(tz)

            station = self.__create_station(short_name, name, altitude, latitude, longitude, status, tz, url)
            self.stations_collection().update({'_id': _id}, {'$set': station}, upsert=True)
            return self.stations_collection().find_one(_id)
        except Exception as e:
            # Unable to update the station based on the provided parameters: return the database version if available
            station = self.stations_collection().find_one(_id)
            if not station:
                raise e
            return station

    def create_measure(self, _id, wind_direction, wind_average, wind_maximum, temperature, humidity,
                       wind_direction_instant=None, wind_minimum=None, pressure=None, luminosity=None, rain=None):

        # Mandatory keys: json 'null' if not present
        measure = {'_id': _id,
                   'w-dir': to_int(wind_direction),
                   'w-avg': to_float(wind_average, 1),
                   'w-max': to_float(wind_maximum, 1),
                   'temp': to_float(temperature, 1),
                   'hum': to_float(humidity, 1)
                   }
        if all((not measure['w-dir'],
                not measure['w-avg'],
                not measure['w-max'],
                not measure['temp'],
                not measure['hum'])):
            raise ProviderException("All mandatory values are null!")

        # Optional keys
        if wind_direction_instant is not None:
            measure['w-inst'] = to_float(wind_direction_instant, 1)
        if wind_minimum is not None:
            measure['w-min'] = to_float(wind_minimum, 1)
        if pressure is not None:
            measure['pres'] = to_int(pressure)
        if luminosity is not None:
            measure['lum'] = to_int(luminosity)
        if rain is not None:
            measure['rain'] = to_float(rain, 1)

        return measure

    def insert_new_measures(self, measure_collection, station, new_measures, logger):
        if len(new_measures) > 0:
            measure_collection.insert(new_measures)

            start_date = arrow.Arrow.fromtimestamp(new_measures[0]['_id'], dateutil.tz.gettz(station['tz']))
            end_date = arrow.Arrow.fromtimestamp(new_measures[-1]['_id'], dateutil.tz.gettz(station['tz']))
            logger.info(
                "--> {end_date} ({end_date_local}), {name} ({id}): {nb} values inserted".format(
                    end_date=end_date.format('YY-MM-DD HH:mm:ssZZ'),
                    end_date_local=end_date.to('local').format('YY-MM-DD HH:mm:ssZZ'),
                    name=station['short'],
                    id=station['_id'],
                    nb=str(len(new_measures))))

    def add_last_measure(self, station_id):
        measures_collection = self.mongo_db[station_id]
        if measures_collection:
            last_measure = measures_collection.find_one({'$query': {}, '$orderby': {'_id': -1}})
            if last_measure:
                self.stations_collection().update({'_id': station_id}, {'$set': {'last': last_measure}})
