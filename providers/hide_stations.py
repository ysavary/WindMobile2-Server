import argparse

import arrow
from pymongo import uri_parser, MongoClient

from provider import get_logger, Status, max_data_age_in_days
from settings import *

logger = get_logger('hide_stations')

parser = argparse.ArgumentParser(description='Hide stations with data older then DAYS')
parser.add_argument('--days', type=int, default=max_data_age_in_days,
                    help="Specify the number of days for the max age of data "
                         "before hiding the station [default: %(default)s]")
args = vars(parser.parse_args())

uri = uri_parser.parse_uri(MONGODB_URL)
client = MongoClient(uri['nodelist'][0][0], uri['nodelist'][0][1])
mongo_db = client[uri['database']]

logger.info("Hiding all stations with data older than {days} days...".format(days=str(args['days'])))

now = arrow.now().timestamp
for station in mongo_db.stations.find({'status': {'$ne': Status.HIDDEN}}):
    last_measure = mongo_db[station['_id']].find_one({'$query': {}, '$orderby': {'_id': -1}})

    if last_measure and last_measure['_id'] < now - max_data_age_in_days * 24 * 3600:
        last = arrow.Arrow.fromtimestamp(last_measure['_id'])
        logger.info("Hiding {id} ['{name}'], last measure at {last}".format(id=station['_id'], name=station['short'],
                                                                            last=last.format('YYYY-MM-DD HH:mm:ssZZ')))
