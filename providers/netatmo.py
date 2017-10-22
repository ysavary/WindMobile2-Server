import requests

from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('netatmo')


class Netatmo(Provider):
    provider_code = 'netatmo'
    provider_name = 'netatmo.com'
    provider_url = 'https://weathermap.netatmo.com'

    def process_data(self):
        try:
            logger.info('Processing Netatmo data...')

            result = requests.post(
                'https://weathermap.netatmo.com/api/getpublicmeasures',
                headers={'authorization': 'Bearer 52d42f05177759882c8b456a|753293ecafa4f4b1a9604611adc998e9'},
                json={'lat_ne': 46.97252415188333, 'lon_ne': 7.707424787402374,
                      'lat_sw': 45.84674058356248, 'lon_sw': 5.966091779589874,
                      'limit': 1024, 'divider': 1, 'type': 'WindStrength', 'date_end': 'last'},
                timeout=(self.connect_timeout, self.read_timeout))

            netatmo_stations = result.json()['body']
            logger.info('Received {nb} Netatmo stations'.format(nb=len(netatmo_stations)))

            for netatmo_station in netatmo_stations:
                station_id = None
                try:
                    netatmo_id = netatmo_station['_id']

                    station = self.save_station(
                        netatmo_id,
                        None,
                        None,
                        netatmo_station['place']['location'][1],
                        netatmo_station['place']['location'][0],
                        Status.GREEN,
                        altitude=netatmo_station['place'].get('altitude', None),
                        tz=netatmo_station['place']['timezone'],
                        url='{url}?stationid={id}'.format(url=self.provider_url, id=netatmo_id),
                    )
                    station_id = station['_id']

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []
                    for netatmo_measure in iter(netatmo_station['measures'].values()):
                        key = int(netatmo_measure['wind_timeutc'])
                        if not self.has_measure(measures_collection, key):
                            try:
                                measure = self.create_measure(
                                    key,
                                    netatmo_measure['wind_angle'],
                                    netatmo_measure['wind_strength'],
                                    netatmo_measure['gust_strength'],
                                )
                                new_measures.append(measure)
                            except ProviderException as e:
                                logger.warn("Error while processing measure '{0}' for station '{1}': {2}"
                                            .format(key, station_id, e))
                            except Exception as e:
                                logger.exception("Error while processing measure '{0}' for station '{1}': {2}"
                                                 .format(key, station_id, e))
                                self.raven_client.captureException()

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing Netatmo: {0}".format(e))
            self.raven_client.captureException()

        logger.info('Done !')


Netatmo().process_data()
