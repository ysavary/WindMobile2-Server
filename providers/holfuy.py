import os
from datetime import datetime, timedelta
import pytz
import json
import re
import urlparse

# Modules
import requests
import xmltodict

from provider import get_logger, Provider, Status, to_float, timestamp

logger = get_logger('holfuy')


class Holfuy(Provider):
    provider_prefix = 'holfuy'
    provider_name = 'holfuy.hu'
    provider_url = 'http://holfuy.hu'

    def __init__(self, mongo_url):
        super(Holfuy, self).__init__(mongo_url)

    def process_data(self):
        try:
            logger.info(u"Processing Holfuy data...")
            result = requests.get("http://holfuy.hu/en/mkrs.php",
                                  timeout=(self.connect_timeout, self.read_timeout))
            result.encoding = 'utf-8'

            xml_files = re.split('<\?xml version=\"1.0\" encoding=\"UTF-8\"\?>', result.text)
            for markers_xml in xml_files[1::]:
                markers_json = xmltodict.parse(markers_xml)['markers']['marker']

                for holfuy_station in markers_json:
                    try:
                        holfuy_id = holfuy_station['@station'][1:]
                        station_id = self.get_station_id(holfuy_id)
                        station = self.save_station(
                            station_id,
                            holfuy_station['@s_name'],
                            holfuy_station['@place'],
                            '',
                            [''],
                            None,
                            holfuy_station['@lat'],
                            holfuy_station['@lng'],
                            Status.GREEN,
                            url=urlparse.urljoin(self.provider_url, "/en/data/" + holfuy_id))

                        measures_collection = self.measures_collection(station_id)
                        new_measures = []

                        now = datetime.now(pytz.utc)
                        local_time = datetime.strptime(holfuy_station['@time'], '%H:%M')
                        try_day = now + timedelta(days=1)
                        while True:
                            date = local_time.replace(year=try_day.year, month=try_day.month, day=try_day.day)
                            date = pytz.timezone(station['tz']).localize(date)
                            if date > now:
                                # The measure is in the future... the measure time seems to be 1 day before (timezone)
                                try_day = try_day - timedelta(days=1)
                            else:
                                break
                        key = timestamp(date)
                        if not measures_collection.find_one(key):
                            measure = self.create_measure(
                                key,
                                holfuy_station['@dir'],
                                to_float(holfuy_station['@speed'], 1) * 3.6,
                                to_float(holfuy_station['@gust'], 1) * 3.6,
                                holfuy_station['@temp'],
                                None)

                            new_measures.append(measure)

                        self.insert_new_measures(measures_collection, station, new_measures, logger)
                        self.add_last_measure(station_id)

                    except Exception as e:
                        logger.error(u"Error while processing station '{0}': {1}".format(json.dumps(holfuy_station), e))

        except Exception as e:
            raise e

        logger.info(u"Done !")


holfuy = Holfuy(os.environ['WINDMOBILE_MONGO_URL'])
holfuy.process_data()