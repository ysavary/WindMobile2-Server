import urllib.parse

import arrow
import requests

from provider import get_logger, Provider, ProviderException, Status
from settings import *

logger = get_logger('pioupiou')


class Pioupiou(Provider):
    provider_code = 'pioupiou'
    provider_name = 'pioupiou.fr'
    provider_url = 'http://pioupiou.fr'

    def get_status(self, status):
        if status == 'on':
            return Status.GREEN
        else:
            return Status.HIDDEN

    def process_data(self):
        try:
            logger.info("Processing Pioupiou data...")
            result = requests.get("http://api.pioupiou.fr/v1/live-with-meta/all",
                                  timeout=(self.connect_timeout, self.read_timeout))

            for piou_station in result.json()['data']:
                try:
                    piou_id = piou_station['id']
                    station_id = self.get_station_id(piou_id)

                    location = piou_station['location']
                    if location['success']:
                        last_location_date = arrow.get(location['date'])
                        if (arrow.utcnow().timestamp - last_location_date.timestamp) > 3600 * 24 * 10:
                            raise ProviderException("Last location date is {0}".format(last_location_date.humanize()))

                    station = self.save_station(
                        station_id,
                        None,
                        None,
                        piou_station['location']['latitude'],
                        piou_station['location']['longitude'],
                        self.get_status(piou_station['status']['state']),
                        url=urllib.parse.urljoin(self.provider_url, str(piou_id)))

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    measure = piou_station['measurements']
                    last_measure_date = arrow.get(measure['date'])
                    key = last_measure_date.timestamp
                    if not measures_collection.find_one(key):
                        measure = self.create_measure(
                            key,
                            measure['wind_heading'],
                            measure['wind_speed_avg'],
                            measure['wind_speed_max'],
                            None,
                            None,
                            pressure=measure['pressure'])

                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)
                    self.add_last_measure(station_id)

                except Exception as e:
                    logger.error("Error while processing station '{0}': {1}".format(station_id, e))

        except Exception as e:
            logger.error("Error while processing PiouPiou: {0}".format(e))

        logger.info("Done !")


pioupiou = Pioupiou(MONGODB_URL, GOOGLE_API_KEY)
pioupiou.process_data()
