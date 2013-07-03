import os

# Modules
import requests

from provider import Status, Category
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
            return Status.HIDDEN
        elif status == 'maintenance':
            return Status.RED
        elif status == 'test':
            return Status.ORANGE
        elif status == 'online':
            return Status.GREEN
        else:
            return Status.HIDDEN

    def get_measure(self, dict, key):
        if key in dict:
            return dict[key]
        else:
            return 0

    def process_data(self):
        try:
            logger.info("Processing JDC data...")
            result = requests.get("http://meteo.jdc.ch/API/?Action=StationView&flags=offline|maintenance|test|online")

            for jdc_station in result.json()['Stations']:
                try:
                    jdc_id = jdc_station['serial']
                    station_id = self.get_station_id(jdc_id)
                    station = {'_id': station_id,
                               'provider': self.provider_name,
                               'short-name': jdc_station['short-name'],
                               'name': jdc_station['name'],
                               'category': Category.PARAGLIDING,
                               'tags': ['switzerland'],
                               'altitude': jdc_station['altitude'],
                               'latitude': jdc_station['latitude'],
                               'longitude': jdc_station['longitude'],
                               'status': self.get_status(jdc_station['status']),
                               'timezone': jdc_station['timezone'],
                               'last-seen': self.now_unix_time()
                               }
                    self.stations_collection.save(station)

                    try:
                        # Asking 2 days of data
                        result = requests.get(
                            "http://meteo.jdc.ch/API/?Action=DataView&serial={jdc_id}&duration=172800".format(
                                jdc_id=jdc_id))
                        if result.json()['ERROR'] == 'OK':
                            measures_collection = self.get_or_create_measures_collection(station_id)

                            measures = result.json()['data']['measurements']
                            new_measures = []
                            for jdc_measure in measures:
                                key = jdc_measure['unix-time']
                                if not measures_collection.find_one(key):
                                    measure = {'_id': key,
                                               'wind-direction': self.get_measure(jdc_measure, 'wind-direction'),
                                               'wind-average': self.get_measure(jdc_measure, 'wind-average'),
                                               'wind-maximum': self.get_measure(jdc_measure, 'wind-maximum'),
                                               'temperature': self.get_measure(jdc_measure, 'temperature'),
                                               'humidity': self.get_measure(jdc_measure, 'humidity')}
                                    new_measures.append(measure)

                            self.insert_new_measures(measures_collection, station, new_measures, logger)

                    except Exception as e:
                        logger.exception("Error while fetching data for station '{0}':".format(station_id))

                    self.add_last_measure(station_id)

                except Exception as e:
                    logger.exception("Error while processing station '{0}':".format(station_id))

        except Exception as e:
            logger.exception("Error while fetching JDC data:")


jdc = Jdc(os.environ['WINDMOBILE_MONGO_URL'])
jdc.process_data()