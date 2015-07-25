import os
from datetime import datetime

# Modules
import requests
import dateutil.parser
import pytz

from provider import get_logger, Provider, ProviderException, timestamp

logger = get_logger('windspots')


class Windspots(Provider):
    provider_prefix = 'windspots'
    provider_name = 'windspots.com'
    provider_url = 'http://www.windspots.com/spots'

    def __init__(self, mongo_url):
        super(Windspots, self).__init__(mongo_url)

    def process_data(self):
        try:
            logger.info(u"Processing WindsSpots data...")
            result = requests.get("http://api.windspots.com/windmobile/stationinfos?allStation=true",
                                  timeout=(self.connect_timeout, self.read_timeout))

            for windspots_station in result.json()['stationInfo']:
                try:
                    windspots_id = windspots_station['@id'][10:]
                    station_id = self.get_station_id(windspots_id)
                    station = self.save_station(
                        station_id,
                        windspots_station['@shortName'],
                        windspots_station['@name'],
                        '',
                        '',
                        windspots_station['@altitude'],
                        windspots_station['@wgs84Latitude'],
                        windspots_station['@wgs84Longitude'],
                        windspots_station['@maintenanceStatus'],
                        url=self.provider_url)

                    try:
                        # Asking 2 days of data
                        result = requests.get(
                            "http://api.windspots.com/windmobile/stationdatas/windspots:{windspots_id}/60"
                            .format(windspots_id=windspots_id), timeout=(self.connect_timeout, self.read_timeout))
                        try:
                            windspots_measure = result.json()
                        except ValueError:
                            raise ProviderException(u"Action=Data return invalid json response")

                        measures_collection = self.measures_collection(station_id)

                        new_measures = []
                        key = timestamp(dateutil.parser.parse(windspots_measure['@lastUpdate']))
                        wind_direction_last = windspots_measure['windDirectionChart']['serie']['points'][0]
                        wind_direction_key = int(wind_direction_last['date']) / 1000
                        if key != wind_direction_key:
                            logger.error(
                                "{station_name} ({station_id}): wind direction '{direction}' is inconsistent "
                                "with measure '{key}'".format(
                                    station_name=station['short'],
                                    station_id=station_id,
                                    key=windspots_measure['@lastUpdate'],
                                    direction=pytz.timezone("Europe/Zurich").localize(datetime.fromtimestamp(wind_direction_key)).strftime(
                                        '%Y-%m-%dT%H:%M:%S%z')))

                        if not measures_collection.find_one(key):
                            try:
                                measure = self.create_measure(
                                    key,
                                    wind_direction_last['value'],
                                    windspots_measure.get('windAverage'),
                                    windspots_measure.get('windMax'),
                                    windspots_measure.get('airTemperature'),
                                    windspots_measure.get('airHumidity'))
                                new_measures.append(measure)
                            except Exception as e:
                                logger.error(u"Error while processing measure '{0}' for station '{1}': {2}"
                                             .format(key, station_id, e))

                        self.insert_new_measures(measures_collection, station, new_measures, logger)

                    except Exception as e:
                        logger.error(u"Error while processing measure for station '{0}': {1}".format(station_id, e))

                    self.add_last_measure(station_id)

                except Exception as e:
                    logger.error(u"Error while processing station '{0}': {1}".format(station_id, e))

        except Exception as e:
            logger.error(u"Error while processing Windspots: {0}".format(e))

        logger.info(u"Done !")


windspots = Windspots(os.environ['WINDMOBILE_MONGO_URL'])
windspots.process_data()
