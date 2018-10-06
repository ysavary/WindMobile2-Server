import collections
import re
from os import path

import requests
from lxml import etree

from commons.provider import get_logger, Provider, ProviderException, Status

logger = get_logger('slf')


class Slf(Provider):
    provider_code = 'slf'
    provider_name = 'slf.ch'
    provider_url = 'https://www.slf.ch'

    provider_urls = {
        'default': 'https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/measured-values.html#windtab',
        'en': 'https://www.slf.ch/en/avalanche-bulletin-and-snow-situation/measured-values.html#windtab',
        'de': 'https://www.slf.ch/de/lawinenbulletin-und-schneesituation/messwerte.html#windtab',
        'fr': 'https://www.slf.ch/fr/bulletin-davalanches-et-situation-nivologique/valeurs-mesurees.html#windtab',
        'it': 'https://www.slf.ch/it/bollettino-valanghe-e-situazione-nivologica/valori-di-misura.html#windtab'
    }

    description_pattern = re.compile(r'<strong>Code:</strong> ([A-Z,0-9]{4})<br/>', re.MULTILINE)
    name_pattern = re.compile(r'(.*?) ([0-9]{2,4}) m')

    Measure = collections.namedtuple(
        'Measure', ('key', 'wind_direction', 'wind_average', 'wind_maximum', 'temperature'))

    def parse_data(self, line) -> Measure:
        values = line.split(';')
        return self.Measure(key=values[0], wind_direction=values[7], wind_average=values[5], wind_maximum=values[6],
                            temperature=values[3])

    def has_wind_data(self, data):
        if not data:
            return False
        measure = self.parse_data(data[-1])
        if measure.key and measure.wind_average and measure.wind_maximum:
            return True

    def add_metadata_from_kml(self, kml_path, slf_metadata):
        with open(path.join(path.dirname(__file__), kml_path)) as kml_file:
            tree = etree.parse(kml_file)
        ns = {'gis': 'http://www.opengis.net/kml/2.2'}

        for placemark in tree.getroot().findall('.//gis:Placemark', namespaces=ns):
            id, = self.description_pattern.search(placemark.find('gis:description', namespaces=ns).text).groups()
            name, _ = self.name_pattern.search(placemark.find('gis:name', namespaces=ns).text).groups()
            lon, lat, altitude = placemark.find('gis:Point/gis:coordinates', namespaces=ns).text.split(',')

            slf_metadata[id] = {
                'name': name,
                'altitude': int(altitude),
                'lat': float(lat),
                'lon': float(lon),
            }

    def process_data(self):
        try:
            logger.info('Processing SLF data...')

            slf_metadata = {}
            self.add_metadata_from_kml('slf/IMIS_WIND_EN.kml', slf_metadata)
            self.add_metadata_from_kml('slf/IMIS_SNOW_EN.kml', slf_metadata)
            self.add_metadata_from_kml('slf/IMIS_SPECIAL_EN.kml', slf_metadata)

            result = requests.get('http://odb.slf.ch/odb/api/v1/stations',
                                  timeout=(self.connect_timeout, self.read_timeout))
            slf_stations = result.json()

            for slf_station in slf_stations:
                station_id = None
                try:
                    slf_id = slf_station['id']
                    result = requests.get("http://odb.slf.ch/odb/api/v1/measurement?id={id}".format(id=slf_id),
                                          timeout=(self.connect_timeout, self.read_timeout))
                    data = result.json()
                    if not self.has_wind_data(data):
                        continue

                    name, altitude = self.name_pattern.search(slf_station['name']).groups()
                    metadata_name, lat, lon = None, None, None
                    if slf_id in slf_metadata:
                        metadata_name = slf_metadata[slf_id]['name']
                        lat = slf_metadata[slf_id]['lat']
                        lon = slf_metadata[slf_id]['lon']
                        status = Status.GREEN
                    else:
                        logger.warn('No metadata found for station {id}/{name}'.format(id=slf_id, name=name))
                        status = Status.ORANGE

                    station = self.save_station(
                        slf_id,
                        metadata_name or name,
                        metadata_name,
                        lat,
                        lon,
                        status,
                        altitude=altitude,
                        url=self.provider_urls)
                    station_id = station['_id']

                    measures = [self.parse_data(line) for line in data]

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []
                    for slf_measure in measures:
                        key = int(slf_measure.key)
                        if not self.has_measure(measures_collection, key):
                            try:
                                measure = self.create_measure(
                                    station,
                                    key,
                                    slf_measure.wind_direction,
                                    slf_measure.wind_average,
                                    slf_measure.wind_maximum,
                                    temperature=slf_measure.temperature,
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
            logger.exception("Error while processing SLF: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Slf().process_data()
