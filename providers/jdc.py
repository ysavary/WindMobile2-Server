import os

# Modules
import requests

from provider import get_logger, Provider, ProviderException, Status, Category

logger = get_logger('jdc')


class Jdc(Provider):
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

    def process_data(self):
        try:
            logger.info(u"Processing JDC data...")
            result = requests.get("http://meteo.jdc.ch/API/?Action=StationView&flags=offline|maintenance|test|online")

            for jdc_station in result.json()['Stations']:
                try:
                    jdc_id = jdc_station['serial']
                    station_id = self.get_station_id(jdc_id)
                    station = self.save_station(
                        station_id,
                        jdc_station['short-name'],
                        jdc_station['name'],
                        Category.PARAGLIDING,
                        ['switzerland'],
                        jdc_station['altitude'],
                        jdc_station['latitude'],
                        jdc_station['longitude'],
                        self.get_status(jdc_station['status']),
                        timezone=jdc_station['timezone'])

                    try:
                        # Asking 2 days of data
                        result = requests.get(
                            "http://meteo.jdc.ch/API/?Action=DataView&serial={jdc_id}&duration=172800"
                            "&flags=offline|maintenance|test|online".format(jdc_id=jdc_id))
                        if result.json()['ERROR'] == 'OK':
                            measures_collection = self.measures_collection(station_id)

                            measures = result.json()['data']['measurements']
                            new_measures = []
                            for jdc_measure in measures:
                                key = jdc_measure['unix-time']
                                if not measures_collection.find_one(key):
                                    measure = self.create_measure(
                                        key,
                                        jdc_measure.get('wind-direction'),
                                        jdc_measure.get('wind-average'),
                                        jdc_measure.get('wind-maximum'),
                                        jdc_measure.get('temperature'),
                                        jdc_measure.get('humidity'),
                                        pressure=jdc_measure.get('pressure', None),
                                        rain=jdc_measure.get('rain', None))
                                    new_measures.append(measure)

                            self.insert_new_measures(measures_collection, station, new_measures, logger)
                        else:
                            raise ProviderException(
                                u"Action=Data return an error: '{0}'".format(result.json()['ERROR']))

                    except (ProviderException, StandardError) as e:
                        logger.error(u"Error while processing measures for station '{0}': {1}".format(station_id, e))

                    self.add_last_measure(station_id)

                except (ProviderException, StandardError) as e:
                    logger.error(u"Error while processing station '{0}': {1}".format(station_id, e))

        except (ProviderException, StandardError) as e:
            logger.error(u"Error while processing JDC: {0}".format(e))

        logger.info(u"Done !")


jdc = Jdc(os.environ['WINDMOBILE_MONGO_URL'])
jdc.process_data()