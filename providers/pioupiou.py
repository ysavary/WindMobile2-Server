import urllib.parse

import arrow
import requests
from arrow.parser import ParserError

from commons.provider import get_logger, Provider, Status, ProviderException, Pressure

logger = get_logger('pioupiou')


class Pioupiou(Provider):
    provider_code = 'pioupiou'
    provider_name = 'pioupiou.com'
    provider_url = 'https://pioupiou.com'

    def get_status(self, station_id, status, location_date, location_status):
        if status == 'on':
            if location_date:
                if (arrow.utcnow().timestamp - location_date.timestamp) < 3600 * 24 * 15:
                    up_to_date = True
                else:
                    logger.warn("'{0}': last known location date is {1}".format(station_id, location_date.humanize()))
                    up_to_date = False
            else:
                logger.warn("'{0}': no last known location".format(station_id))
                return Status.RED

            if location_status and up_to_date:
                return Status.GREEN
            else:
                return Status.ORANGE
        else:
            return Status.HIDDEN

    def process_data(self):
        try:
            logger.info("Processing Pioupiou data...")
            result = requests.get("http://api.pioupiou.fr/v1/live-with-meta/all", timeout=(self.connect_timeout,
                                                                                           self.read_timeout))
            station_id = None
            for piou_station in result.json()['data']:
                try:
                    piou_id = piou_station['id']
                    location = piou_station['location']
                    latitude = location.get('latitude')
                    longitude = location.get('longitude')
                    if (latitude is None or longitude is None) or (latitude == 0 and longitude == 0):
                        continue

                    location_date = None
                    if location['date']:
                        try:
                            location_date = arrow.get(location['date'])
                        except ParserError:
                            pass

                    station = self.save_station(
                        piou_id,
                        None,
                        None,
                        latitude,
                        longitude,
                        self.get_status(station_id, piou_station['status']['state'], location_date,
                                        location['success']),
                        url=urllib.parse.urljoin(self.provider_url, str(piou_id)),
                        default_name=piou_station.get('meta', {}).get('name', None))
                    station_id = station['_id']

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    piou_measure = piou_station['measurements']
                    last_measure_date = arrow.get(piou_measure['date'])
                    key = last_measure_date.timestamp
                    if not self.has_measure(measures_collection, key):
                        measure = self.create_measure(
                            station,
                            key,
                            piou_measure['wind_heading'],
                            piou_measure['wind_speed_avg'],
                            piou_measure['wind_speed_max'],
                            pressure=Pressure(qfe=piou_measure['pressure'], qnh=None, qff=None)
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing Pioupiou: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Pioupiou().process_data()
