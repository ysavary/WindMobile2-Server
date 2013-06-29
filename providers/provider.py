import os
import logging
import sys
import logging.handlers
from pymongo import MongoClient, uri_parser
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


class Category:
    TAKEOFF = 'takeoff'
    LANDING = 'landing'
    KITE = 'kite'


class Provider(object):
    def __init__(self, mongo_url):
        uri = uri_parser.parse_uri(mongo_url)
        client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
        self.mongo_db = client[uri['database']]
        self.stations_collection = self.mongo_db.stations

    def get_station_id(self, id):
        return self.provider_prefix + "-" + str(id)

    def clean_stations_collection(self):
        self.stations_collection.remove({'provider': self.provider_name})

    def get_or_create_measures_collection(self, station_id):
        try:
            kwargs = {'capped': True, 'size': 500000, 'max': 5000}
            return self.mongo_db.create_collection(station_id, **kwargs)
        except CollectionInvalid:
            return self.mongo_db[station_id]

    def add_last_measure(self, station_id):
        measures_collection = self.mongo_db[station_id]
        if measures_collection:
            last_measure = measures_collection.find_one({'$query': {}, '$orderby': {'_id': -1}})
            if last_measure:
                self.stations_collection.update({'_id': station_id}, {'$set': {'last-measure': last_measure}},
                                                upsert=False)



