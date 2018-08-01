import re

import arrow
import requests
from dateutil import tz
from lxml import html

from provider import get_logger, Provider, Status, ProviderException

logger = get_logger('iweathar')


class IWeathar(Provider):
    provider_code = 'iweathar'
    provider_name = 'iweathar.co.za'
    provider_url = 'http://iweathar.co.za'

    def process_data(self):
        try:
            logger.info("Processing iWeathar data...")

            list_pattern = re.compile(r"marker = new PdMarker\(new GLatLng\((?P<lat>[+-]?([0-9]*[.])?[0-9]+), "
                                      r"(?P<lon>[+-]?([0-9]*[.])?[0-9]+)\), icon(.*?)"
                                      r"var html = \"(?P<name>.*?)<br><a href=\\'display\.php\?s_id=(?P<id>[0-9]+)\\'",
                                      flags=re.DOTALL)

            speed_pattern = re.compile(r'In the last few minutes the wind was (.*?) at an '
                                       r'average speed of (?P<avg>[0-9]+) kmh, reaching up to (?P<max>[0-9]+) kmh')

            dir_pattern = re.compile(r'.{1,3} (?P<dir>[0-9]+)')
            temp_pattern = re.compile(r'(?P<temp>-?([0-9]+[.])?[0-9]?)')
            hum_pattern = re.compile(r'(?P<hum>[0-9]{1,2})')

            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                                  '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'})

            content = session.get(self.provider_url + '/google_maps.php',
                                  timeout=(self.connect_timeout, self.read_timeout), verify=False).text

            stations_jsons = []
            for match in list_pattern.finditer(content):
                stations_jsons.append(match.groupdict())

            iweathar_tz = tz.gettz('Africa/Johannesburg')

            for stations_json in stations_jsons:
                station_id = None
                try:
                    url = self.provider_url + '/display?s_id=' + stations_json['id']
                    station = self.save_station(
                        stations_json['id'],
                        stations_json['name'],
                        stations_json['name'],
                        float(stations_json['lat']),
                        float(stations_json['lon']),
                        Status.GREEN,
                        url=url
                    )
                    station_id = station['_id']

                    html_tree = html.fromstring(
                        session.get(url, timeout=(self.connect_timeout, self.read_timeout), verify=False).text)

                    date = html_tree.xpath('//*[text()="Last Update:"]/../following::td')[0].text.strip()
                    key = arrow.get(date, 'YYYY-MM-DD HH:mm:ss').replace(tzinfo=iweathar_tz).timestamp

                    try:
                        dir_text = html_tree.xpath('//*[text()="Wind Direction:"]/../following::td/a')[0].text.strip()
                        dir_match = dir_pattern.match(dir_text).groupdict()
                        wind_dir = dir_match['dir']

                        speed_text = html_tree.xpath('//*[text()="Weather Summary:"]/../following::td')[0].text.strip()
                        speed_match = speed_pattern.match(speed_text).groupdict()
                        wind_avg = speed_match['avg']
                        wind_max = speed_match['max']
                    except:
                        raise ProviderException('Unable to get wind measures')

                    try:
                        temp_text = html_tree.xpath('//*[text()="Temperature:"]/../following::td/a')[0].text.strip()
                        temp_match = temp_pattern.match(temp_text).groupdict()
                        temp = temp_match['temp']
                    except:
                        temp = None

                    try:
                        hum_text = html_tree.xpath('//*[text()="Humidity:"]/../following::td/a')[0].text.strip()
                        hum_match = hum_pattern.match(hum_text).groupdict()
                        hum = hum_match['hum']
                    except:
                        hum = None

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    if not self.has_measure(measures_collection, key):
                        measure = self.create_measure(
                            key,
                            wind_dir,
                            wind_avg,
                            wind_max,
                            temperature=temp,
                            humidity=hum,
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing iWeathar: {0}".format(e))
            self.raven_client.captureException()

        logger.info("...Done!")


IWeathar().process_data()
