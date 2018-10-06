import arrow
import arrow.parser
import requests

from commons.provider import get_logger, Provider, ProviderException

logger = get_logger('windspots')


class Windspots(Provider):
    provider_code = 'windspots'
    provider_name = 'windspots.com'
    provider_url = 'https://www.windspots.com'

    def process_data(self):
        try:
            logger.info("Processing WindsSpots data...")
            result = requests.get("https://api.windspots.com/windmobile/stationinfos?allStation=true",
                                  timeout=(self.connect_timeout, self.read_timeout), verify=False)

            for windspots_station in result.json()['stationInfo']:
                station_id = None
                try:
                    windspots_id = windspots_station['@id'][10:]
                    station = self.save_station(
                        windspots_id,
                        windspots_station['@shortName'],
                        windspots_station['@name'],
                        windspots_station['@wgs84Latitude'],
                        windspots_station['@wgs84Longitude'],
                        windspots_station['@maintenanceStatus'],
                        altitude=windspots_station['@altitude'])
                    station_id = station['_id']

                    try:
                        # Asking 2 days of data
                        result = requests.get(
                            "https://api.windspots.com/windmobile/stationdatas/windspots:{windspots_id}".format(
                                windspots_id=windspots_id),
                            timeout=(self.connect_timeout, self.read_timeout), verify=False)
                        try:
                            windspots_measure = result.json()
                        except ValueError:
                            raise ProviderException("Action=Data return invalid json response")

                        measures_collection = self.measures_collection(station_id)

                        new_measures = []
                        try:
                            # Weird, there are timezone mistakes in windspots provider!
                            key = arrow.get(windspots_measure['@lastUpdate']).replace(tzinfo='Europe/Zurich').timestamp
                        except arrow.parser.ParserError:
                            raise ProviderException("Unable to parse measure date: '{0}".format(
                                windspots_measure['@lastUpdate']))

                        wind_direction_last = windspots_measure['windDirectionChart']['serie']['points'][0]
                        wind_direction_key = int(wind_direction_last['date']) // 1000
                        if arrow.get(key).minute != arrow.get(wind_direction_key).minute:
                            logger.warn(
                                "{name} ({id}): wind direction time '{direction}' is inconsistent with measure "
                                "time '{key}'"
                                .format(
                                    name=station['short'],
                                    id=station_id,
                                    key=arrow.get(key).to('local').format('YY-MM-DD HH:mm:ssZZ'),
                                    direction=arrow.get(wind_direction_key).to('local').format('YY-MM-DD HH:mm:ssZZ')))

                        if not self.has_measure(measures_collection, key):
                            try:
                                measure = self.create_measure(
                                    station,
                                    key,
                                    wind_direction_last['value'],
                                    windspots_measure.get('windAverage'),
                                    windspots_measure.get('windMax'),
                                    temperature=windspots_measure.get('airTemperature'),
                                    humidity=windspots_measure.get('airHumidity'),
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
                        logger.warn("Error while processing measure for station '{0}': {1}".format(station_id, e))
                    except Exception as e:
                        logger.exception("Error while processing measure for station '{0}': {1}".format(station_id, e))
                        self.raven_client.captureException()

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn("Error while processing Windspots: {0}".format(e))
        except Exception as e:
            logger.exception("Error while processing Windspots: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Windspots().process_data()
