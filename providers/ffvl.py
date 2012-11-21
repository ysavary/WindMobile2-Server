import os
import time
from datetime import datetime
import xml.etree.ElementTree as ET

# Modules
import requests
import pymongo

import provider

logger = provider.get_logger('ffvl')

class Ffvl(provider.Provider):
    provider = 'ffvl'

    def __init__(self, mongo_url, api_key):
        super(Ffvl, self).__init__(mongo_url)
        self.api_key = api_key

    # FFVL status: 0, 1
    def get_status(self, status):
        if status == 0:
            return 'red'
        elif status == '1':
            return 'green'
        else:
            return "hidden"

    def get_tags(self, ffvl_station):
        tags = []
        tags.append('france')
        tags.append(ffvl_station.find('departement').attrib['value'])
        return tags


    def put_xml_element(self, dict, key, xml_element, xml_child_name, conversion_function=None, mandatory=True):
        child = xml_element.find(xml_child_name)
        if not child is None:
            value = child.text
            if not value is None:
                if conversion_function:
                    dict[key] = conversion_function(value)
                else:
                    dict[key] = value
                return
        if mandatory:
            dict[key] = None

    def put_xml_attribute(self, dict, key, xml_element, xml_child_name, conversion_function=None, mandatory=True):
            child = xml_element.find(xml_child_name)
        if not child is None:
            value = child.text
            if not value is None:
                if conversion_function:
                    dict[key] = conversion_function(value)
                else:
                    dict[key] = value
                return
        if mandatory:
            dict[key] = None


    def process_data(self):
        try:
            logger.info("Processing FFVL data...")

            result = requests.get("http://data.ffvl.fr/xml/" + api_key + "/meteo/balise_list.xml")
            ffvl_stations = ET.fromstring(result.text)

            self.clean_stations_collection()
            for ffvl_station in ffvl_stations:
                try:
                    station_id = self.get_station_id(ffvl_station.find('idBalise').text)
                    station = {'_id': station_id,
                               'provider': self.provider }
                    'category': 'paragliding',
                'tags_fr': self.get_tags(ffvl_station),
                'timezone': '+01:00',

                    self.put_xml_in_dict(station, 'short-name', ffvl_station, 'nom')
                    self.put_xml_in_dict(station, 'name', ffvl_station, 'nom')
                    self.put_xml_in_dict(station, 'description', ffvl_station, 'description', mandatory=False)
                    self.put_xml_in_dict(station, 'url', ffvl_station, 'url', mandatory=False)
                    self.put_xml_in_dict(station, 'altitude', ffvl_station, 'directVentMoy')
                    self.put_xml_in_dict(station, 'longitude', ffvl_station, 'directVentMoy')
                self.put_xml_in_dict(station, 'status', ffvl_station, 'active')


                               'short-name': self.put_xml_in_dict()ffvl_station.find('nom').text,
                               'name': ffvl_station.find('nom').text,
                               'description': ffvl_station.find('description').text,
                               'url': ffvl_station.find('url').attrib['value'],

                               'altitude': int(ffvl_station.find('altitude').attrib['value']),
                               'latitude': float(ffvl_station.find('coord').attrib['lat']),
                               'longitude': float(ffvl_station.find('coord').attrib['lon']),
                               'status': self.get_status(ffvl_station.find('active').text),

                    }
                    self.stations_collection.insert(station)

                except Exception as e:
                    logger.exception("Error while processing station '{0}':".format(station_id))

        except Exception as e:
            logger.exception("Error while fetching FFVL stations:")

        try:
            result = requests.get("http://data.ffvl.fr/xml/" + api_key + "/meteo/relevemeteo.xml")
            ffvl_measures = ET.fromstring(result.text)

            for ffvl_measure in ffvl_measures:
                try:
                    station_id = self.get_station_id(ffvl_measure.find('idbalise').text)
                    try:
                        kwargs = {'capped': True, 'size': 500000, 'max': 5000}
                        values_collection = self.mongo_db.create_collection(station_id, **kwargs)
                    except pymongo.errors.CollectionInvalid:
                        values_collection = self.mongo_db[station_id]

                    date = datetime.strptime(ffvl_measure.find('date').text, '%Y-%m-%d %H:%M:%S')
                    key = int(time.mktime(date.timetuple()))
                    if not values_collection.find_one(key):
                        measure = {'_id': key}
                        self.put_xml_in_dict(measure, 'wind-direction', ffvl_measure, 'directVentMoy', int)
                        self.put_xml_in_dict(measure, 'wind-average', ffvl_measure, 'vitesseVentMoy', float)
                        self.put_xml_in_dict(measure, 'wind-maximum', ffvl_measure, 'vitesseVentMax', float)
                        self.put_xml_in_dict(measure, 'wind-minimum', ffvl_measure, 'vitesseVentMin', float, False)
                        self.put_xml_in_dict(measure, 'temperature', ffvl_measure, 'temperature', float)
                        self.put_xml_in_dict(measure, 'humidity', ffvl_measure, 'hydrometrie', int)
                        values_collection.insert(measure)

                except Exception as e:
                    logger.exception("Error while processing measures for station '{0}':".format(station_id))

        except Exception as e:
            logger.exception("Error while fetching FFVL measures:")

ffvl = Ffvl(os.environ['WINDMOBILE_MONGO_URL'], os.environ['WINDMOBILE_FFVL_KEY'])
ffvl.process_data()