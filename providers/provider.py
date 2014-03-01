import sys
import os
import logging
import logging.handlers
from time import time
from datetime import datetime
from pymongo import uri_parser, MongoClient, GEOSPHERE
from pymongo.errors import CollectionInvalid


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
            # Limit file to 5Mb
            handler = logging.handlers.RotatingFileHandler(
                os.path.join(os.environ['WINDMOBILE_LOG_DIR'], name + '.log'), maxBytes=5 * 10 ** 6)
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


class Category:
    PARAGLIDING = 'para'
    KITE = 'kite'


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value, ndigits=None):
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return None


class Provider(object):
    def __init__(self, mongo_url):
        uri = uri_parser.parse_uri(mongo_url)
        client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
        self.mongo_db = client[uri['database']]

    def stations_collection(self):
        collection = self.mongo_db.stations
        collection.ensure_index([('loc', GEOSPHERE)])
        collection.ensure_index([('name', 'text'), ('desc', 'text')], language='french')
        return collection

    def measures_collection(self, station_id):
        try:
            return self.mongo_db.create_collection(station_id, **{'capped': True, 'size': 500000, 'max': 5000})
        except CollectionInvalid:
            return self.mongo_db[station_id]

    def get_station_id(self, id):
        return self.provider_prefix + "-" + str(id)

    def now_unix_time(self):
        return int(time())

    def __create_station(self, short_name, name, category, tags, altitude, latitude, longitude, status,
                         description=None, url=None, timezone=None, uptime=None, language=None):

        station = {'prov': self.provider_name,
                   'short': short_name,
                   'name': name,
                   'cat': category,
                   'tags': tags,
                   'alt': to_int(altitude),
                   'loc': {
                       'lat': to_float(latitude, 6),
                       'lon': to_float(longitude, 6)
                   },
                   'status': status,
                   'seen': self.now_unix_time()
                   }

        # Optional keys
        if description:
            station['desc'] = description
        if url:
            station['url'] = url
        if timezone:
            station['timezone'] = timezone
        if uptime:
            station['uptime'] = uptime
        if language:
            station['language'] = language

        return station

    def save_station(self, _id, short_name, name, category, tags, altitude, latitude, longitude, status,
                     description=None, url=None, timezone=None, uptime=None, language=None):

        station = self.__create_station(short_name, name, category, tags, altitude, latitude, longitude, status,
                                        description, url, timezone, uptime, language)
        self.stations_collection().update({'_id': _id}, {'$set': station}, upsert=True)
        return self.stations_collection().find_one(_id)

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

        # Optional keys
        if wind_direction_instant is not None:
            measure['w-inst'] = to_float(wind_direction_instant, 1),
        if wind_minimum is not None:
            measure['w-min'] = to_float(wind_minimum, 1),
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

            start_date = datetime.fromtimestamp(new_measures[0]['_id'])
            end_date = datetime.fromtimestamp(new_measures[-1]['_id'])
            logger.info("--> from " + start_date.strftime('%Y-%m-%dT%H:%M:%S') + " to " +
                        end_date.strftime('%Y-%m-%dT%H:%M:%S') + ", " + station['short'] +
                        " (" + station['_id'] + "): " + str(len(new_measures)) + " values inserted")

    def add_last_measure(self, station_id):
        measures_collection = self.mongo_db[station_id]
        if measures_collection:
            last_measure = measures_collection.find_one({'$query': {}, '$orderby': {'_id': -1}})
            if last_measure:
                self.stations_collection().update({'_id': station_id}, {'$set': {'last': last_measure}})
