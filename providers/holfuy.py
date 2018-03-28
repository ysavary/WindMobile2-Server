import arrow
import arrow.parser
import requests

from provider import Q_, ureg
from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('holfuy')


class Holfuy(Provider):
    provider_code = 'holfuy'
    provider_name = 'holfuy.hu'
    provider_url = 'http://holfuy.hu'

    def process_data(self):
        try:
            logger.info("Processing Holfuy data...")
            holfuy_stations = requests.get("http://api.holfuy.com/stations/stations.json",
                                           timeout=(self.connect_timeout, self.read_timeout)).json()
            holfuy_data = requests.get("http://api.holfuy.com/live/?s=all&m=JSON&tu=C&su=km/h&utc",
                                       timeout=(self.connect_timeout, self.read_timeout)).json()
            holfuy_measures = {}
            for measure in holfuy_data['measurements']:
                holfuy_measures[measure['stationId']] = measure

            for holfuy_station in holfuy_stations['holfuyStationsList']:
                station_id = None
                try:
                    holfuy_id = holfuy_station['id']
                    name = holfuy_station['name']
                    location = holfuy_station['location']
                    latitude = location.get('latitude')
                    longitude = location.get('longitude')
                    if (latitude is None or longitude is None) or (latitude == 0 and longitude == 0):
                        continue
                    altitude = location.get('altitude')

                    station = self.save_station(
                        holfuy_id,
                        name,
                        name,
                        latitude,
                        longitude,
                        Status.GREEN,
                        altitude=altitude)
                    station_id = station['_id']

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    measure = holfuy_measures[holfuy_id]
                    last_measure_date = arrow.get(measure['dateTime'])
                    key = last_measure_date.timestamp
                    if not self.has_measure(measures_collection, key):
                        measure = self.create_measure(
                            key,
                            measure['wind']['direction'],
                            Q_(measure['wind']['speed'], ureg.kilometer / ureg.hour),
                            Q_(measure['wind']['gust'], ureg.kilometer / ureg.hour),
                            temperature=Q_(measure['temperature'], ureg.degC) if 'temperature' in measure else None,
                            pressure=Q_(measure['pressure'], ureg.Pa * 100) if 'pressure' in measure else None
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing Holfuy: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Holfuy().process_data()
