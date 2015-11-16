import argparse
import os
# Modules
import arrow
from pymongo import uri_parser, MongoClient

from provider import get_logger

logger = get_logger('delete_stations')

parser = argparse.ArgumentParser(description='Delete stations not seen since DAYS')
parser.add_argument('--days', type=int, default=60, help="Specify the number of days since 'last seen' "
                                                         "before deleting the station [default: %(default)s]")
args = vars(parser.parse_args())

uri = uri_parser.parse_uri(os.environ['WINDMOBILE_MONGO_URL'])
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]

logger.info("Deleting all stations not seen since {days} days...".format(days=str(args['days'])))

now = arrow.now().timestamp
for station in mongo_db.stations.find({'seen': {'$lt': now - args['days'] * 3600 * 24}}):
    seen = arrow.Arrow.fromtimestamp(station['seen'])
    logger.info("Deleting {id} ['{name}'], last seen at {seen}".format(id=station['_id'], name=station['short'],
                                                                       seen=seen.format('YYYY-MM-DD HH:mm:ssZZ')))
    mongo_db[station['_id']].drop()
    mongo_db.stations.remove({'_id': station['_id']})
