import arrow
import requests
from dateutil import tz

from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('ffvl')


class Ffvl(Provider):
    provider_code = 'ffvl'
    provider_name = 'ffvl.fr'
    provider_url = 'http://www.balisemeteo.com'

    def process_data(self):
        try:
            logger.info('Processing FFVL data...')

            result = requests.get('http://data.ffvl.fr/json/balises.json', timeout=(self.connect_timeout,
                                                                                    self.read_timeout))
            ffvl_stations = result.json()

            for ffvl_station in ffvl_stations:
                station_id = None
                try:
                    ffvl_id = ffvl_station['idBalise']
                    station = self.save_station(
                        ffvl_id,
                        ffvl_station['nom'],
                        ffvl_station['nom'],
                        ffvl_station['latitude'],
                        ffvl_station['longitude'],
                        Status.GREEN,
                        altitude=ffvl_station['altitude'],
                        url=ffvl_station['url'])
                    station_id = station['_id']

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn('Error while processing stations: {0}'.format(e))
        except Exception as e:
            logger.exception('Error while processing stations: {0}'.format(e))
            self.raven_client.captureException()

        try:
            result = requests.get('http://data.ffvl.fr/json/relevesmeteo.json', timeout=(self.connect_timeout,
                                                                                         self.read_timeout))
            ffvl_measures = result.json()

            ffvl_tz = tz.gettz('Europe/Paris')
            for ffvl_measure in ffvl_measures:
                try:
                    ffvl_id = ffvl_measure['idbalise']
                    station_id = self.get_station_id(ffvl_id)
                    station = self.stations_collection().find_one(station_id)
                    if not station:
                        raise ProviderException("Unknown station '{0}'".format(station_id))

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    key = arrow.get(ffvl_measure['date'], 'YYYY-MM-DD HH:mm:ss').replace(tzinfo=ffvl_tz).timestamp

                    if not self.has_measure(measures_collection, key):
                        measure = self.create_measure(
                            key,
                            ffvl_measure['directVentMoy'],
                            ffvl_measure['vitesseVentMoy'],
                            ffvl_measure['vitesseVentMax'],
                            temperature=ffvl_measure['temperature'],
                            humidity=ffvl_measure['hydrometrie'],
                            pressure=ffvl_measure['pression'],
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing measures for station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing measures for station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn('Error while processing FFVL: {0}', e)
        except Exception as e:
            logger.exception('Error while processing FFVL: {0}', e)
            self.raven_client.captureException()

        logger.info('...Done!')


Ffvl().process_data()
