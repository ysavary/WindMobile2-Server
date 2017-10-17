import arrow
import requests
from lxml import html

from projections import ch_to_wgs_lat, ch_to_wgs_lon
from provider import get_logger, Provider, Status, ProviderException, Q_, ureg

logger = get_logger('meteoswiss')


class MeteoSwiss(Provider):
    provider_code = 'meteoswiss'
    provider_name = 'meteoswiss.ch'
    provider_url = 'http://www.meteosuisse.admin.ch'

    provider_urls = {
        'default': 'http://www.meteosuisse.admin.ch/home/meteo/valeurs-de-mesures/valeurs-de-mesures-aux-stations.html'
                   '?param=wind-combination&station={id}',
        'en': 'http://www.meteosuisse.admin.ch/home/meteo/valeurs-de-mesures/valeurs-de-mesures-aux-stations.html'
              '?param=wind-combination&station={id}',
        'de': 'http://www.meteoschweiz.admin.ch/home/wetter/messwerte/messwerte-an-stationen.html'
              '?param=wind-combination&station={id}',
        'fr': 'http://www.meteosuisse.admin.ch/home/meteo/valeurs-de-mesures/valeurs-de-mesures-aux-stations.html'
              '?param=wind-combination&station={id}',
        'it': 'http://www.meteosvizzera.admin.ch/home/tempo/misurazioni/misurazioni-delle-stazioni.html'
              '?param=wind-combination&station={id}'
    }

    def process_data(self):
        try:
            logger.info("Processing MeteoSwiss data...")

            base_url = 'http://www.meteoswiss.admin.ch'
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 '
                                                  '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'})

            main_url = '/home/weather/measurement-values/measurement-values-at-meteorological-stations.html'
            html_tree = html.fromstring(
                session.get(base_url + main_url, timeout=(self.connect_timeout, self.read_timeout)).text)

            # Main wind data
            element = html_tree.xpath('//input[@id="measurement__param-radio--wind"]')[0]
            data_json_url = element.get('data-json-url')
            wind_datas = session.get(base_url + data_json_url,
                                     timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Temperature data
            element = html_tree.xpath('//input[@id="measurement__param-radio--temperature"]')[0]
            data_json_url = element.get('data-json-url')
            temp_datas = session.get(base_url + data_json_url,
                                     timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Humidity data
            element = html_tree.xpath('//input[@id="measurement__param-radio--humidity"]')[0]
            data_json_url = element.get('data-json-url')
            humidity_datas = session.get(base_url + data_json_url,
                                         timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Pressure data
            element = html_tree.xpath('//input[@id="measurement__param-radio--airpressure"]')[0]
            data_json_url = element.get('data-json-url')
            pressure_datas = session.get(base_url + data_json_url,
                                         timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Rain data
            element = html_tree.xpath('//input[@id="measurement__param-radio--precipitation"]')[0]
            data_json_url = element.get('data-json-url')
            rain_datas = session.get(base_url + data_json_url,
                                     timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            for wind_data in wind_datas:
                station_id = None
                try:
                    urls = {}
                    for key, value in self.provider_urls.items():
                        urls[key] = value.format(id=wind_data['id'].lower())

                    station = self.save_station(
                        wind_data['id'],
                        wind_data['city_name'],
                        wind_data['city_name'],
                        ch_to_wgs_lat(int(wind_data['coord_x']), int(wind_data['coord_y'])),
                        ch_to_wgs_lon(int(wind_data['coord_x']), int(wind_data['coord_y'])),
                        Status.GREEN,
                        altitude=wind_data['evelation'],
                        tz='Europe/Zurich',
                        url=urls)
                    station_id = station['_id']

                    key = arrow.get(int(wind_data['date'])/1000).timestamp

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []

                    if not self.has_measure(measures_collection, key):
                        temp_data = None
                        for data in temp_datas:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                temp_data = data

                        humidity_data = None
                        for data in humidity_datas:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                humidity_data = data

                        pressure_data = None
                        for data in pressure_datas:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                pressure_data = data

                        rain_data = None
                        for data in rain_datas:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                rain_data = data

                        wind_dir = None
                        if wind_data['current_value'][2] is not None:
                            wind_dir = Q_(wind_data['current_value'][2], ureg.degree)

                        wind_avg = None
                        if wind_data['current_value'][0] is not None:
                            wind_avg = Q_(wind_data['current_value'][0], ureg.kilometer / ureg.hour)

                        wind_max = None
                        if wind_data['current_value'][1] is not None:
                            wind_max = Q_(wind_data['current_value'][1], ureg.kilometer / ureg.hour)

                        temp = None
                        if temp_data and temp_data['current_value'] is not None:
                            temp = Q_(temp_data['current_value'], ureg.degC)

                        humidity = None
                        if humidity_data and humidity_data['current_value'] is not None:
                            humidity = humidity_data['current_value']

                        pressure = None
                        if pressure_data and pressure_data['current_value'] is not None:
                            pressure = Q_(pressure_data['current_value'], ureg.Pa * 100)

                        rain = None
                        if rain_data and rain_data['current_value'] is not None:
                            rain = Q_(rain_data['current_value'], ureg.liter / (ureg.meter ** 2))

                        measure = self.create_measure(
                            key,
                            wind_dir,
                            wind_avg,
                            wind_max,
                            temperature=temp,
                            humidity=humidity,
                            pressure=pressure,
                            rain=rain,
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing station '{0}': {1}".format(station_id, e))
                except Exception as e:
                    logger.exception("Error while processing station '{0}': {1}".format(station_id, e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing MeteoSwiss: {0}".format(e))
            self.raven_client.captureException()

        logger.info("...Done!")


MeteoSwiss().process_data()
