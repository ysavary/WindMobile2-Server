import os
import logging
import logging.handlers
from pymongo import Connection, uri_parser

def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if os.environ.has_key('WINDMOBILE_LOG_DIR'):
        # Limit file to 5Mb
        handler = logging.handlers.RotatingFileHandler(os.path.join(os.environ(['WINDMOBILE_LOG_DIR'], name + '.log'), maxBytes=5 * 10 ** 6))
        fmt = logging.Formatter('%(asctime)s %(levelname)s [%(name)s]: %(message)s', '%Y-%m-%dT%H:%M:%S%z')
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    # Console
    handler = logging.StreamHandler()
    fmt = logging.Formatter('%(levelname)s [%(name)s]: %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    return logger


class Provider(object):
    def __init__(self, mongo_url):
        connection = Connection(mongo_url)
        db_name = uri_parser.parse_uri(mongo_url)['database']
        self.mongo_db = connection[db_name]
        self.stations_collection = self.mongo_db.stations

    def get_station_id(self, id):
        return self.provider + "_" + str(id)

    def clean_stations_collection(self):
        self.stations_collection.remove({'provider': self.provider})
