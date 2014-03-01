from windmobile import settings

from django.core.management.base import BaseCommand
from optparse import make_option
from pymongo import uri_parser, MongoClient
from time import time

from logging import getLogger
logger = getLogger('provider.test')

class Command(BaseCommand):
    help = u"Remove stations not seen since {--days=60} days"
    option_list = BaseCommand.option_list + (
        make_option('--days',
                    action='store_true',
                    dest='days',
                    default=60,
                    help=u"Specify the number of days since 'last seen' "
                         u"before removing the station [default: %default]"),)

    def handle(self, *args, **options):
        uri = uri_parser.parse_uri(settings.MONGODB_URL)
        client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
        self.mongo_db = client[uri['database']]

        now = int(time())

        for station in self.mongo_db.stations.find():
            logger.info(station['short'])
            if station['seen'] + options['days'] * 3600 * 24 < now:
                self.stdout.write(station['short'])