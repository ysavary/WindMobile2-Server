import os
import time
from datetime import datetime
import xml.etree.ElementTree as ET

# Modules
import requests

from provider import get_logger, Provider, ProviderException, Status, Category

logger = get_logger('ffvl')


class Ffvl(Provider):
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

    def get_xml_element(self, xml_element, xml_child_name):
        child = xml_element.find(xml_child_name)
        if not child is None:
            return child.text

        return None

    def get_xml_attribute(self, xml_element, xml_child_name, xml_child_attrib):
        child = xml_element.find(xml_child_name)
        if not child is None:
            return child.attrib[xml_child_attrib]

        return None

    def get_category(self, xml_element):
        try:
            child = xml_element.find('forKyte')
            if int(child.text) == 1:
                return Category.KITE
        except (AttributeError, ValueError):
            pass
        return Category.PARAGLIDING

    def process_data(self):
        try:
            logger.info(u"Processing FFVL data...")

            result = requests.get("http://data.ffvl.fr/xml/" + self.api_key + "/meteo/balise_list.xml")
            ffvl_stations = ET.fromstring(result.text)

            for ffvl_station in ffvl_stations:
                try:
                    station_id = self.get_station_id(ffvl_station.find('idBalise').text)

                    station = self.create_station(
                        station_id,
                        self.get_xml_element(ffvl_station, 'nom'),
                        self.get_xml_element(ffvl_station, 'nom'),
                        self.get_category(ffvl_station),
                        self.get_tags(ffvl_station),
                        self.get_xml_attribute(ffvl_station, 'altitude', 'value'),
                        self.get_xml_attribute(ffvl_station, 'coord', 'lat'),
                        self.get_xml_attribute(ffvl_station, 'coord', 'lon'),
                        self.get_status(self.get_xml_element(ffvl_station, 'active')),
                        description=self.get_xml_element(ffvl_station, 'description'),
                        url=self.get_xml_attribute(ffvl_station, 'url', 'value'))
                    self.stations_collection().save(station)

                except (ProviderException, StandardError) as e:
                    logger.error(u"Error while processing station '{0}': {1}".format(station_id, e))

        except (ProviderException, StandardError) as e:
            logger.error(u"Error while processing stations: {0}".format(e))

        try:
            result = requests.get("http://data.ffvl.fr/xml/" + self.api_key + "/meteo/relevemeteo.xml")
            ffvl_measures = ET.fromstring(result.text)

            for ffvl_measure in ffvl_measures:
                try:
                    station_id = self.get_station_id(ffvl_measure.find('idbalise').text)
                    station = self.stations_collection().find_one(station_id)
                    if not station:
                        raise ProviderException(u"Unknown station '{0}'".format(station_id))

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    date = datetime.strptime(ffvl_measure.find('date').text, '%Y-%m-%d %H:%M:%S')
                    key = int(time.mktime(date.timetuple()))
                    if not measures_collection.find_one(key):
                        measure = self.create_measure(
                            key,
                            self.get_xml_element(ffvl_measure, 'directVentMoy'),
                            self.get_xml_element(ffvl_measure, 'vitesseVentMoy'),
                            self.get_xml_element(ffvl_measure, 'vitesseVentMax'),
                            self.get_xml_element(ffvl_measure, 'temperature'),
                            self.get_xml_element(ffvl_measure, 'hydrometrie'),
                            wind_direction_instant=self.get_xml_element(ffvl_measure, 'directVentInst'),
                            wind_minimum=self.get_xml_element(ffvl_measure, 'vitesseVentMin'),
                            pressure=self.get_xml_element(ffvl_measure, 'pression'),
                            luminosity=self.get_xml_element(ffvl_measure, 'luminosite'))

                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except (ProviderException, StandardError) as e:
                    logger.error(u"Error while processing measures for station '{0}': {1}".format(station_id, e))

                self.add_last_measure(station_id)

        except (ProviderException, StandardError) as e:
            logger.error(u"Error while processing measures: {0}", e)

        logger.info(u"...Done!")

ffvl = Ffvl(os.environ['WINDMOBILE_MONGO_URL'], os.environ['WINDMOBILE_FFVL_KEY'])
ffvl.process_data()