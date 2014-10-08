from time import time
from datetime import datetime

from django.core.management.base import BaseCommand
from optparse import make_option
from pymongo import uri_parser, MongoClient

from windmobile import settings

from logging import getLogger
logger = getLogger("provider.cleanup")

class Command(BaseCommand):
    help = u"Remove stations not seen since {--days=60} days"
    option_list = BaseCommand.option_list + (
        make_option('--days',
                    dest='days',
                    default="60",
                    help=u"Specify the number of days since 'last seen' "
                         u"before removing the station [default: %default]"),)

    def __init__(self):
        super(Command, self).__init__()

        uri = uri_parser.parse_uri(settings.MONGODB_URL)
        client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
        self.mongo_db = client[uri['database']]

    def handle(self, *args, **options):
        logger.info("Deleting all stations not seen since " + options['days'] + " days...")

        now = int(time())
        for station in self.mongo_db.stations.find():
            if station['seen'] + int(options['days']) * 3600 * 24 < now:
                seen = datetime.fromtimestamp(station['seen']).strftime('%Y-%m-%d %H:%M:%S')
                logger.info("Deleting " + station['_id'] + "['" + station['short'] + "'], last seen at " + seen)
                self.mongo_db.stations.remove({'_id': station['_id']})