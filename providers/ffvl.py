import os
import time
from datetime import datetime
import xml.etree.ElementTree as ET

# Modules
import requests

import provider
from provider import Status, Category

logger = provider.get_logger('ffvl')


class Ffvl(provider.Provider):
    provider_prefix = 'ffvl'
    provider_name = 'ffvl.fr'

    def __init__(self, mongo_url, api_key):
        super(Ffvl, self).__init__(mongo_url)
        self.api_key = api_key

    # FFVL active: '0', '1'
    def get_status(self, status):
        if status == '0':
            return Status.RED
        elif status == '1':
            return Status.GREEN
        else:
            return Status.HIDDEN

    def get_tags(self, ffvl_station):
        return ['france', ffvl_station.find('departement').attrib['value']]

    def put_xml_element(self, dict, key, xml_element, xml_child_name, conversion_function=None, default=None):
        child = xml_element.find(xml_child_name)
        if not child is None:
            value = child.text
            if not value is None:
                if conversion_function:
                    dict[key] = conversion_function(value)
                else:
                    dict[key] = value
            else:
                if default:
                    dict[key] = default

    def put_xml_attribute(self, dict, key, xml_element, xml_child_name, xml_child_attrib, conversion_function=None,
                          default=None):
        child = xml_element.find(xml_child_name)
        if not child is None:
            value = child.attrib[xml_child_attrib]
            if not value is None:
                if conversion_function:
                    dict[key] = conversion_function(value)
                else:
                    dict[key] = value
            else:
                if default:
                    dict[key] = default

    def is_kite(self, xml_element):
        try:
            child = xml_element.find('forKyte')
            return int(child.text) == 1
        except:
            return False

    def process_data(self):
        try:
            logger.info("Processing FFVL data...")

            result = requests.get("http://data.ffvl.fr/xml/" + self.api_key + "/meteo/balise_list.xml")
            ffvl_stations = ET.fromstring(result.text)

            for ffvl_station in ffvl_stations:
                try:
                    station_id = self.get_station_id(ffvl_station.find('idBalise').text)
                    station = {'_id': station_id,
                               'provider': self.provider_name,
                               'tags': self.get_tags(ffvl_station),
                               'last-seen': self.now_unix_time()
                               }

                    if self.is_kite(ffvl_station):
                        station['category'] = Category.KITE
                    else:
                        station['category'] = Category.PARAGLIDING

                    self.put_xml_element(station, 'short-name', ffvl_station, 'nom')
                    self.put_xml_element(station, 'name', ffvl_station, 'nom')
                    self.put_xml_element(station, 'description', ffvl_station, 'description')
                    self.put_xml_attribute(station, 'url', ffvl_station, 'url', 'value')
                    self.put_xml_attribute(station, 'altitude', ffvl_station, 'altitude', 'value', int)
                    self.put_xml_attribute(station, 'latitude', ffvl_station, 'coord', 'lat', float)
                    self.put_xml_attribute(station, 'longitude', ffvl_station, 'coord', 'lon', float)
                    self.put_xml_element(station, 'status', ffvl_station, 'active', self.get_status, 'hidden')

                    self.stations_collection.save(station)

                except Exception as e:
                    logger.exception("Error while processing station '{0}':".format(station_id))

        except Exception as e:
            logger.exception("Error while fetching FFVL stations:")

        try:
            result = requests.get("http://data.ffvl.fr/xml/" + self.api_key + "/meteo/relevemeteo.xml")
            ffvl_measures = ET.fromstring(result.text)

            for ffvl_measure in ffvl_measures:
                try:
                    station_id = self.get_station_id(ffvl_measure.find('idbalise').text)
                    station = self.stations_collection.find_one(station_id)

                    measures_collection = self.get_or_create_measures_collection(station_id)
                    new_measures = []

                    date = datetime.strptime(ffvl_measure.find('date').text, '%Y-%m-%d %H:%M:%S')
                    key = int(time.mktime(date.timetuple()))
                    if not measures_collection.find_one(key):
                        measure = {'_id': key}
                        self.put_xml_element(measure, 'wind-direction', ffvl_measure, 'directVentMoy', int)
                        self.put_xml_element(measure, 'wind-average', ffvl_measure, 'vitesseVentMoy', float)
                        self.put_xml_element(measure, 'wind-maximum', ffvl_measure, 'vitesseVentMax', float)
                        self.put_xml_element(measure, 'wind-minimum', ffvl_measure, 'vitesseVentMin', float)
                        self.put_xml_element(measure, 'temperature', ffvl_measure, 'temperature', float)
                        self.put_xml_element(measure, 'humidity', ffvl_measure, 'hydrometrie', float, -1)

                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except Exception as e:
                    logger.exception("Error while processing measures for station '{0}':".format(station_id))

                self.add_last_measure(station_id)

        except Exception as e:
            logger.exception("Error while fetching FFVL measures:")

ffvl = Ffvl(os.environ['WINDMOBILE_MONGO_URL'], os.environ['WINDMOBILE_FFVL_KEY'])
ffvl.process_data()