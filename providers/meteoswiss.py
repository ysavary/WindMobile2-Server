import io
import json
from os import path

import arrow
import requests

from provider import get_logger, Provider, Status, ProviderException

logger = get_logger('meteoswiss')


class MeteoSwiss(Provider):
    provider_code = 'meteoswiss'
    provider_name = 'meteoswiss.ch'
    provider_url = 'http://www.meteoswiss.ch'

    def process_data(self):
        try:
            logger.info("Processing MeteoSwiss data...")

            with open(path.join(path.dirname(__file__), 'meteoswiss/vqha69.json')) as in_file:
                descriptions = json.load(in_file)

            data_file = io.StringIO(requests.get("http://data.geo.admin.ch/ch.meteoschweiz.swissmetnet/VQHA69.csv",
                                                 headers={'Accept': '*/*', 'User-Agent': 'winds.mobi'},
                                                 timeout=(self.connect_timeout, self.read_timeout)).text)
            lines = data_file.readlines()
            keys = lines[2].strip().split('|')

            for line in lines[3:]:
                station_id = None
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
                        description['location']['lat'],
                        description['location']['lon'],
                        Status.GREEN,
                        altitude=description['altitude'],
                        tz='Europe/Zurich')

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

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except ProviderException as e:
            logger.warn("Error while processing MeteoSwiss: {0}".format(e))
        except Exception as e:
            logger.exception("Error while processing MeteoSwiss: {0}".format(e))
            self.raven_client.captureException()

        logger.info("...Done!")

MeteoSwiss().process_data()
