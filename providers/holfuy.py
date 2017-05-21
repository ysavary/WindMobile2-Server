import re
import urllib.parse
from datetime import datetime, timedelta

import pytz
import requests
import xmltodict

from provider import get_logger, Provider, Status, to_float, ProviderException

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
            for markers_xml in xml_files[1:]:
                markers_json = xmltodict.parse(markers_xml)['markers']['marker']

                for holfuy_station in markers_json:
                    station_id = None
                    try:
                        if '@station' not in holfuy_station:
                            continue
                        holfuy_id = holfuy_station['@station'][1:]
                        name = holfuy_station['@place']
                        station = self.save_station(
                            holfuy_id,
                            name,
                            name,
                            holfuy_station['@lat'],
                            holfuy_station['@lng'],
                            Status.GREEN,
                            url=urllib.parse.urljoin(self.provider_url, "/en/data/" + holfuy_id))
                        station_id = station['_id']

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
                        if not self.has_measure(measures_collection, key):
                            measure = self.create_measure(
                                key,
                                holfuy_station['@dir'],
                                to_float(holfuy_station['@speed'], 1) * 3.6,
                                to_float(holfuy_station['@gust'], 1) * 3.6,
                                holfuy_station['@temp'],
                                None)

                            new_measures.append(measure)

                        self.insert_new_measures(measures_collection, station, new_measures, logger)

                    except ProviderException as e:
                        logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                    except Exception as e:
                        logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                        self.raven_client.captureException()

        except ProviderException as e:
            logger.warn("Error while processing Holfuy: {0}".format(e))
        except Exception as e:
            logger.exception("Error while processing Holfuy: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Holfuy().process_data()
