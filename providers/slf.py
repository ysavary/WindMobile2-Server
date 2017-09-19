import collections
import re
from xml.etree import ElementTree

import requests

from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('slf')


class Slf(Provider):
    provider_code = 'slf'
    provider_name = 'slf.ch'
    provider_url = 'http://www.slf.ch/schneeinfo/messwerte/wt-daten/index_EN'

    station_metadata_name_regexp = r'(.{3}-[0-9]{1}) : (.*? - .*?) \(IMIS\)'
    station_name_regexp = r'(.*?)([0-9]{3,4}) m'

    Measure = collections.namedtuple(
        'Measure', ['key', 'wind_direction', 'wind_average', 'wind_maximum', 'temperature'])

    def parse_data(self, line) -> Measure:
        values = line.split(';')
        return self.Measure(values[0], values[7], values[5], values[6], values[3])

    def has_wind_data(self, data):
        if not data:
            return False
        measure = self.parse_data(data[-1])
        if measure.key and measure.wind_average and measure.wind_maximum:
            return True

    def process_data(self):
        try:
            logger.info("Processing SLF data...")

            slf_metadata = {}
            tree = ElementTree.parse('slf/SLF Messtationen Standorte.kml')
            ns = {'gis': 'http://www.opengis.net/kml/2.2'}
            for placemark in tree.getroot().findall('.//gis:Placemark', namespaces=ns):
                id, name = re.search(
                    self.station_metadata_name_regexp, placemark.find('gis:name', namespaces=ns).text).groups()
                lon, lat = placemark.find('gis:Point/gis:coordinates', namespaces=ns).text.split(',')
                slf_metadata[id.replace('-', '')] = {
                    'name': name,
                    'lat': float(lat),
                    'lon': float(lon),
                }

            result = requests.get("http://odb.slf.ch/odb/api/v1/stations",
                                  timeout=(self.connect_timeout, self.read_timeout))

            try:
                slf_stations = result.json()
            except:
                raise Exception("Unable to get SLF station list")

            for slf_station in slf_stations:
                station_id = None
                try:
                    slf_id = slf_station['id']
                    result = requests.get("http://odb.slf.ch/odb/api/v1/measurement?id={id}".format(id=slf_id),
                                          timeout=(self.connect_timeout, self.read_timeout))
                    data = result.json()
                    if not self.has_wind_data(data):
                        continue

                    name, altitude = re.search(self.station_name_regexp, slf_station['name']).groups()
                    metadata_name, lat, lon = None, None, None
                    if slf_id in slf_metadata:
                        metadata_name = slf_metadata[slf_id]['name']
                        lat = slf_metadata[slf_id]['lat']
                        lon = slf_metadata[slf_id]['lon']
                    else:
                        logger.warn('No metadata found for station {id}/{name}'.format(id=slf_id, name=name))

                    station = self.save_station(
                        slf_id,
                        metadata_name or name,
                        metadata_name,
                        lat,
                        lon,
                        Status.GREEN,
                        altitude=altitude)
                    station_id = station['_id']

                    measures = [self.parse_data(line) for line in data]

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []
                    for slf_measure in measures:
                        key = int(slf_measure.key)
                        if not self.has_measure(measures_collection, key):
                            try:
                                measure = self.create_measure(
                                    key,
                                    slf_measure.wind_direction,
                                    slf_measure.wind_average,
                                    slf_measure.wind_maximum,
                                    slf_measure.temperature,
                                    None)
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
            logger.exception("Error while processing SLF: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Slf().process_data()
