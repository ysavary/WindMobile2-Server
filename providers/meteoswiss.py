import io
import os
import json

# Modules
import requests
import arrow

from provider import get_logger, Provider, Status

logger = get_logger('meteoswiss')


class MeteoSwiss(Provider):
    provider_prefix = 'meteoswiss'
    provider_name = 'meteoswiss.ch'
    provider_url = 'http://www.meteoswiss.ch'

    def __init__(self, mongo_url):
        super().__init__(mongo_url)

    def process_data(self):
        try:
            logger.info("Processing METEOSWISS data...")

            with open(os.path.join(os.path.dirname(__file__), 'meteoswiss/vqha69.json')) as in_file:
                descriptions = json.load(in_file)

            data_file = io.StringIO(
                requests.get("http://data.geo.admin.ch/ch.meteoschweiz.swissmetnet/VQHA69.txt").text)
            lines = data_file.readlines()
            keys = lines[2].strip().split('|')

            for line in lines[3:]:
                try:
                    data = {}
                    for i, key in enumerate(keys):
                        values = line.strip().split('|')
                        if values[i] != '-':
                            data[key] = values[i]
                        else:
                            data[key] = None

                    description = descriptions[data['stn']]

                    station_id = self.get_station_id(data['stn'])
                    station = self.save_station(
                        station_id,
                        description['name'],
                        description['name'],
                        '',
                        ['switzerland'],
                        description['altitude'],
                        description['location']['lat'],
                        description['location']['lon'],
                        Status.GREEN)

                    key = arrow.get(data['time'], 'YYYYMMDDHHmm').timestamp

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    if not measures_collection.find_one(key):
                        measure = self.create_measure(
                            key,
                            data['dkl010z0'],
                            data['fu3010z0'],
                            data['fu3010z1'],
                            data['tre200s0'],
                            data['ure200s0'],
                            pressure=data['prestas0'],
                            rain=data['rre150z0'],
                            luminosity=data['sre000z0'])
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)
                    self.add_last_measure(station_id)

                except Exception as e:
                    logger.error("Error while processing station '{0}': {1}".format(station_id, e))

        except Exception as e:
            logger.error("Error while processing METEOSWISS: {0}".format(e))

        logger.info("...Done!")

meteoswiss = MeteoSwiss(os.environ['WINDMOBILE_MONGO_URL'])
meteoswiss.process_data()
