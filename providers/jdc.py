import os
from datetime import datetime

# Modules
import requests
import pymongo

import provider

logger = provider.get_logger('jdc')

class Jdc(provider.Provider):
    provider_prefix = 'jdc'
    provider_name = 'jdc.ch'

    def __init__(self, mongo_url):
        super(Jdc, self).__init__(mongo_url)

    # Jdc status: offline, maintenance, test or online
    def get_status(self, status):
        if status == 'offline':
            return 'hidden'
        elif status == 'maintenance':
            return 'red'
        elif status == 'test':
            return 'orange'
        elif status == 'online':
            return 'green'
        else:
            return "hidden"


    def get_measure(self, dict, key):
        if key in dict:
            return dict[key]
        else:
            return 0

    def process_data(self):
        try:
            logger.info("Processing JDC data...")
            result = requests.get("http://meteo.jdc.ch/API/?Action=StationView&flags=offline|maintenance|test|online")

            self.clean_stations_collection()
            for jdc_station in result.json['Stations']:
                try:
                    jdc_id = jdc_station['serial']
                    station_id = self.get_station_id(jdc_id)
                    station = {'_id': station_id,
                               'provider': self.provider_name,
                               'short-name': jdc_station['short-name'],
                               'name': jdc_station['name'],
                               'category': 'takeoff',
                               'tags': None,
                               'altitude': jdc_station['altitude'],
                               'latitude': jdc_station['latitude'],
                               'longitude': jdc_station['longitude'],
                               'status': self.get_status(jdc_station['status']),
                               'timezone': jdc_station['timezone'],
                    }
                    self.stations_collection.insert(station)

                    try:
                        # Asking 2 days of data
                        result = requests.get(
                            "http://meteo.jdc.ch/API/?Action=DataView&serial={jdc_id}&duration=172800".format(
                                jdc_id=jdc_id))
                        if result.json['ERROR'] == 'OK':
                            try:
                                kwargs = {'capped': True, 'size': 500000, 'max': 5000}
                                values_collection = self.mongo_db.create_collection(station_id, **kwargs)
                            except pymongo.errors.CollectionInvalid:
                                values_collection = self.mongo_db[station_id]

                            measures = result.json['data']['measurements']
                            new_measures = []
                            for jdc_measure in measures:
                                key = jdc_measure['unix-time']
                                if not values_collection.find_one(key):
                                    measure = {'_id': key,
                                               'wind-direction': self.get_measure(jdc_measure, 'wind-direction'),
                                               'wind-average': self.get_measure(jdc_measure, 'wind-average'),
                                               'wind-maximum': self.get_measure(jdc_measure, 'wind-maximum'),
                                               'temperature': self.get_measure(jdc_measure, 'temperature'),
                                               'humidity': self.get_measure(jdc_measure, 'humidity')}
                                    values_collection.insert(measure)
                                    new_measures.append(measure)

                            if len(new_measures) > 0:
                                start_date = datetime.fromtimestamp(new_measures[0]['_id'])
                                end_date = datetime.fromtimestamp(new_measures[-1]['_id'])
                                logger.info(
                                    "--> from " + start_date.strftime('%Y-%m-%dT%H:%M:%S') + " to " + end_date.strftime('%Y-%m-%dT%H:%M:%S') + ", " +
                                    station['short-name'] + " (" + station_id + "): " + str(len(new_measures)) + " values inserted")

                    except Exception as e:
                        logger.exception("Error while fetching data for station '{0}':".format(station_id))

                except Exception as e:
                    logger.exception("Error while processing station '{0}':".format(station_id))

        except Exception as e:
            logger.exception("Error while fetching JDC data:")


jdc = Jdc(os.environ['WINDMOBILE_MONGO_URL'])
jdc.process_data()