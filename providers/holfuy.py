import json
import re
import urllib.parse
from datetime import datetime, timedelta

import pytz
import requests
import xmltodict

from provider import get_logger, Provider, Status, to_float
from settings import *

logger = get_logger('holfuy')


class Holfuy(Provider):
    provider_code = 'holfuy'
    provider_name = 'holfuy.hu'
    provider_url = 'http://holfuy.hu'

    def process_data(self):
        try:
            logger.info("Processing Holfuy data...")
            result = requests.get("http://holfuy.hu/en/mkrs.php", timeout=(self.connect_timeout, self.read_timeout))
            result.encoding = 'utf-8'

            xml_files = re.split('<\?xml version=\"1.0\" encoding=\"UTF-8\"\?>', result.text)
            for markers_xml in xml_files[1::]:
                markers_json = xmltodict.parse(markers_xml)['markers']['marker']

                for holfuy_station in markers_json:
                    try:
                        holfuy_id = holfuy_station['@station'][1:]
                        station_id = self.get_station_id(holfuy_id)
                        name = holfuy_station['@place']
                        station = self.save_station(
                            station_id,
                            name,
                            name,
                            holfuy_station['@lat'],
                            holfuy_station['@lng'],
                            Status.GREEN,
                            url=urllib.parse.urljoin(self.provider_url, "/en/data/" + holfuy_id))

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
                        key = date.timestamp()
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
                        logger.error("Error while processing station '{0}': {1}".format(json.dumps(holfuy_station), e))

        except Exception as e:
            raise e

        logger.info("Done !")


holfuy = Holfuy(MONGODB_URL, GOOGLE_API_KEY)
holfuy.process_data()