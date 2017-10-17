import urllib.parse

import requests

from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('jdc')


class Jdc(Provider):
    provider_code = 'jdc'
    provider_name = 'jdc.ch'
    provider_url = 'http://meteo.jdc.ch'

    # Jdc status: offline, maintenance, test or online
    def get_status(self, status):
        if status == 'offline':
            return Status.HIDDEN
        elif status == 'maintenance':
            return Status.RED
        elif status == 'test':
            return Status.ORANGE
        elif status == 'online':
            return Status.GREEN
        else:
            return Status.HIDDEN

    def process_data(self):
        try:
            logger.info("Processing JDC data...")
            result = requests.get("http://meteo.jdc.ch/API/?Action=StationView&flags=all",
                                  timeout=(self.connect_timeout, self.read_timeout))

            try:
                jdc_stations = result.json()['Stations']
            except:
                raise Exception("Action=StationView returns invalid json response")

            for jdc_station in jdc_stations:
                station_id = None
                try:
                    jdc_id = jdc_station['serial']
                    station = self.save_station(
                        jdc_id,
                        jdc_station['short-name'],
                        jdc_station['name'],
                        jdc_station['latitude'],
                        jdc_station['longitude'],
                        self.get_status(jdc_station['status']),
                        altitude=jdc_station['altitude'],
                        url=urllib.parse.urljoin(self.provider_url, "/station/" + str(jdc_station['serial'])))
                    station_id = station['_id']

                    try:
                        # Asking 2 days of data
                        result = requests.get("http://meteo.jdc.ch/API/?Action=DataView&serial={jdc_id}&duration=172800"
                                              .format(jdc_id=jdc_id), timeout=(self.connect_timeout, self.read_timeout))
                        try:
                            json = result.json()
                        except ValueError:
                            raise Exception("Action=DataView returns invalid json response")
                        if json['ERROR'] == 'OK':
                            measures_collection = self.measures_collection(station_id)

                            measures = json['data']['measurements']
                            new_measures = []
                            for jdc_measure in measures:
                                key = jdc_measure['unix-time']
                                if not self.has_measure(measures_collection, key):
                                    try:
                                        measure = self.create_measure(
                                            key,
                                            jdc_measure.get('wind-direction'),
                                            jdc_measure.get('wind-average'),
                                            jdc_measure.get('wind-maximum'),
                                            temperature=jdc_measure.get('temperature'),
                                            humidity=jdc_measure.get('humidity'),
                                            pressure=jdc_measure.get('pressure', None),
                                            rain=jdc_measure.get('rain', None),
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
                        else:
                            raise ProviderException("Action=Data returns an error: '{0}'".format(json['ERROR']))

                    except ProviderException as e:
                        logger.warn("Error while processing measures for station '{0}': {1}".format(station_id, e))
                    except Exception as e:
                        logger.exception("Error while processing measures for station '{0}': {1}".format(station_id, e))
                        self.raven_client.captureException()

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing JDC: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Jdc().process_data()
