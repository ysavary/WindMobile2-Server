from datetime import datetime

import requests
from pytz import timezone

from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('ffvl')


class Ffvl(Provider):
    provider_code = 'ffvl'
    provider_name = 'ffvl.fr'
    provider_url = 'http://www.balisemeteo.com'

    def process_data(self):
        try:
            logger.info("Processing FFVL data...")

            result = requests.get("http://data.ffvl.fr/json/balises.json", timeout=(self.connect_timeout,
                                                                                    self.read_timeout))

            for ffvl_station in result.json():
                station_id = None
                try:
                    ffvl_id = ffvl_station['idBalise']
                    station_id = self.get_station_id(ffvl_id)

                    self.save_station(
                        station_id,
                        ffvl_station['nom'],
                        ffvl_station['nom'],
                        ffvl_station['latitude'],
                        ffvl_station['longitude'],
                        Status.GREEN,
                        altitude=ffvl_station['altitude'],
                        url=ffvl_station['url'])

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn("Error while processing stations: {0}".format(e))
        except Exception as e:
            logger.exception("Error while processing stations: {0}".format(e))
            self.raven_client.captureException()

        try:
            result = requests.get("http://data.ffvl.fr/json/relevesmeteo.json", timeout=(self.connect_timeout,
                                                                                         self.read_timeout))

            ffvl_tz = timezone('Europe/Paris')
            for ffvl_measure in result.json():
                try:
                    ffvl_id = ffvl_measure['idbalise']
                    station_id = self.get_station_id(ffvl_id)
                    station = self.stations_collection().find_one(station_id)
                    if not station:
                        raise ProviderException("Unknown station '{0}'".format(station_id))

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    key = int(
                        ffvl_tz.localize(datetime.strptime(ffvl_measure['date'], '%Y-%m-%d %H:%M:%S')).timestamp())

                    if not measures_collection.find_one(key):
                        measure = self.create_measure(
                            key,
                            ffvl_measure['directVentMoy'],
                            ffvl_measure['vitesseVentMoy'],
                            ffvl_measure['vitesseVentMax'],
                            ffvl_measure['temperature'],
                            ffvl_measure['hydrometrie'],
                            pressure=ffvl_measure['pression'],
                            luminosity=ffvl_measure['luminosite'])

                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing measures for station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing measures for station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

                self.add_last_measure(station_id)

        except ProviderException as e:
            logger.warn("Error while processing FFVL: {0}", e)
        except Exception as e:
            logger.exception("Error while processing FFVL: {0}", e)
            self.raven_client.captureException()

        logger.info("...Done!")

Ffvl().process_data()
