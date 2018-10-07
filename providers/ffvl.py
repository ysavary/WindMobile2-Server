from json import JSONDecodeError

import arrow
import requests
from dateutil import tz

from commons.provider import get_logger, Provider, ProviderException, Status, Pressure

logger = get_logger('ffvl')


class Ffvl(Provider):
    provider_code = 'ffvl'
    provider_name = 'ffvl.fr'
    provider_url = 'http://www.balisemeteo.com'

    def process_data(self):
        stations = {}
        try:
            logger.info('Processing FFVL data...')

            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                                  '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'})

            result = session.get('http://data.ffvl.fr/json/balises.json', timeout=(self.connect_timeout,
                                                                                    self.read_timeout))
            ffvl_stations = result.json()

            for ffvl_station in ffvl_stations:
                ffvl_id = None
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
                    stations[station['_id']] = station

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(ffvl_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(ffvl_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn('Error while processing stations: {0}'.format(e))
        except Exception as e:
            logger.exception('Error while processing stations: {0}'.format(e))
            self.raven_client.captureException()

        try:
            result = session.get('http://data.ffvl.fr/json/relevesmeteo.json', timeout=(self.connect_timeout,
                                                                                         self.read_timeout))
            try:
                ffvl_measures = result.json()
            except JSONDecodeError as e:
                logger.error(f"Unable to parse 'relevesmeteo.json', status_code={result.status_code}: '{result.text}'")
                raise e

            ffvl_tz = tz.gettz('Europe/Paris')
            for ffvl_measure in ffvl_measures:
                station_id = None
                try:
                    ffvl_id = ffvl_measure['idbalise']
                    station_id = self.get_station_id(ffvl_id)
                    if station_id not in stations:
                        raise ProviderException("Unknown station '{0}'".format(station_id))
                    station = stations[station_id]

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    key = arrow.get(ffvl_measure['date'], 'YYYY-MM-DD HH:mm:ss').replace(tzinfo=ffvl_tz).timestamp

                    if not self.has_measure(measures_collection, key):
                        measure = self.create_measure(
                            station,
                            key,
                            ffvl_measure['directVentMoy'],
                            ffvl_measure['vitesseVentMoy'],
                            ffvl_measure['vitesseVentMax'],
                            temperature=ffvl_measure['temperature'],
                            humidity=ffvl_measure['hydrometrie'],
                            pressure=Pressure(qfe=ffvl_measure['pression'], qnh=None, qff=None)
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing measures for station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing measures for station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn("Error while processing FFVL: '{0}'".format(e))
        except Exception as e:
            logger.exception("Error while processing FFVL: '{0}'".format(e))
            self.raven_client.captureException()

        logger.info('...Done!')


Ffvl().process_data()
