import re

import arrow
import requests
from dateutil import tz

from provider import get_logger, Provider, Status, ProviderException

logger = get_logger('yvbeach')


class YVBeach(Provider):
    provider_code = 'yvbeach'
    provider_name = 'yvbeach.com'
    provider_url = 'http://www.yvbeach.com/yvmeteo.htm'

    def process_data(self):
        station_id = 'yvbeach'
        try:
            logger.info("Processing yvbeach data...")

            date_pattern = re.compile(r'Relevés du<br/>(?P<date>.*?) à (?P<time>.*?)<br/>')
            wind_pattern = re.compile(r'<b>VENT</b><br/>'
                                      r'Moy10min <b>(?P<wind_avg>[0-9]{1,3}\.[0-9]) km/h</b><br/>'
                                      r'Max/1h <b>(?P<wind_max>[0-9]{1,3}\.[0-9]) km/h<br/>.{2} - (?P<wind_dir>[0-9]{2})°')

            yvbeach_tz = tz.gettz('Europe/Zurich')

            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                                  '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'})
            content = session.get('http://www.yvbeach.com/yvmeteo.wml',
                                    timeout=(self.connect_timeout, self.read_timeout)).text.replace('\r\n', '')

            station = self.save_station(
                'yvbeach',
                'yvbeach',
                'Yvonand plage',
                float(46.806048),
                float(6.738763),
                Status.GREEN,
                url=self.provider_url
            )
            station_id = station['_id']

            date = date_pattern.search(content).groupdict()
            key = arrow.get('{0} {1}'.format(date['date'], date['time']), 'DD.MM.YYYY HH[h]mm').replace(
                tzinfo=yvbeach_tz).timestamp

            measures_collection = self.measures_collection(station_id)
            new_measures = []

            if not self.has_measure(measures_collection, key):
                wind = wind_pattern.search(content).groupdict()

                temp_pattern = re.compile(r'<b>TEMPERATURES<br/>Air (?P<temp>[-+]?[0-9]*\.?[0-9]+)°C')
                temp = temp_pattern.search(content).groupdict()

                measure = self.create_measure(
                    key,
                    wind['wind_dir'],
                    wind['wind_avg'],
                    wind['wind_max'],
                    temperature=temp['temp'],
                )
                new_measures.append(measure)

            self.insert_new_measures(measures_collection, station, new_measures, logger)

        except ProviderException as e:
            logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
        except Exception as e:
            logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
            self.raven_client.captureException()

        logger.info("...Done!")


YVBeach().process_data()
