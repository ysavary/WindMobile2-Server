import arrow
import requests
from lxml import html

from commons import user_agents
from commons.projections import ch_to_wgs_lat, ch_to_wgs_lon
from commons.provider import Provider, Status, ProviderException, Q_, ureg, Pressure


class MeteoSwiss(Provider):
    provider_code = 'meteoswiss'
    provider_name = 'meteoswiss.ch'
    provider_url = 'https://www.meteoswiss.admin.ch'

    provider_urls = {
        'default': 'https://www.meteoswiss.admin.ch'
                   '/home/weather/measurement-values/measurement-values-at-meteorological-stations.html'
                   '?param=wind-combination&station={id}',
        'en': 'https://www.meteoswiss.admin.ch'
              '/home/weather/measurement-values/measurement-values-at-meteorological-stations.html'
              '?param=wind-combination&station={id}',
        'de': 'https://www.meteoschweiz.admin.ch'
              '/home/wetter/messwerte/messwerte-an-stationen.html'
              '?param=wind-combination&station={id}',
        'fr': 'https://www.meteosuisse.admin.ch'
              '/home/meteo/valeurs-de-mesures/valeurs-de-mesures-aux-stations.html'
              '?param=wind-combination&station={id}',
        'it': 'https://www.meteosvizzera.admin.ch'
              '/home/tempo/misurazioni/misurazioni-delle-stazioni.html'
              '?param=wind-combination&station={id}'
    }

    def process_data(self):
        try:
            self.log.info('Processing MeteoSwiss data...')

            base_url = 'https://www.meteoswiss.admin.ch'
            session = requests.Session()
            session.headers.update(user_agents.chrome)

            main_url = '/home/weather/measurement-values/measurement-values-at-meteorological-stations.html'
            html_tree = html.fromstring(
                session.get(base_url + main_url, timeout=(self.connect_timeout, self.read_timeout)).text)

            # Main wind data
            element = html_tree.xpath('//input[@id="measurement__param-radio--wind"]')[0]
            wind_datas = session.get(base_url + element.get('data-json-url'),
                                     timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Temperature data
            element = html_tree.xpath('//input[@id="measurement__param-radio--temperature"]')[0]
            temp_datas = session.get(base_url + element.get('data-json-url'),
                                     timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Humidity data
            element = html_tree.xpath('//input[@id="measurement__param-radio--humidity"]')[0]
            humidity_datas = session.get(base_url + element.get('data-json-url'),
                                         timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Pressure data
            element = html_tree.xpath('//option[@id="measurement__param-option--airpressure-qfe"]')[0]
            pressure_datas_qfe = session.get(base_url + element.get('data-json-url'),
                                             timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            element = html_tree.xpath('//option[@id="measurement__param-option--airpressure-qnh"]')[0]
            pressure_datas_qnh = session.get(base_url + element.get('data-json-url'),
                                             timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            element = html_tree.xpath('//option[@id="measurement__param-option--airpressure-qff"]')[0]
            pressure_datas_qff = session.get(base_url + element.get('data-json-url'),
                                             timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            # Rain data
            element = html_tree.xpath('//input[@id="measurement__param-radio--precipitation"]')[0]
            rain_datas = session.get(base_url + element.get('data-json-url'),
                                     timeout=(self.connect_timeout, self.read_timeout)).json()['stations']

            for wind_data in wind_datas:
                station_id = None
                try:
                    urls = {lang: url.format(id=wind_data['id'].lower()) for lang, url in self.provider_urls.items()}
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

                        pressure_data_qfe = None
                        for data in pressure_datas_qfe:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                pressure_data_qfe = data

                        pressure_data_qnh = None
                        for data in pressure_datas_qnh:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                pressure_data_qnh = data

                        pressure_data_qff = None
                        for data in pressure_datas_qff:
                            if data['id'] == wind_data['id'] and data['date'] == wind_data['date']:
                                pressure_data_qff = data

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

                        qfe = None
                        if pressure_data_qfe and pressure_data_qfe['current_value'] is not None:
                            qfe = Q_(pressure_data_qfe['current_value'], ureg.hPa)

                        qnh = None
                        if pressure_data_qnh and pressure_data_qnh['current_value'] is not None:
                            qnh = Q_(pressure_data_qnh['current_value'], ureg.hPa)

                        qff = None
                        if pressure_data_qff and pressure_data_qff['current_value'] is not None:
                            qff = Q_(pressure_data_qff['current_value'], ureg.hPa)

                        rain = None
                        if rain_data and rain_data['current_value'] is not None:
                            rain = Q_(rain_data['current_value'], ureg.liter / (ureg.meter ** 2))

                        measure = self.create_measure(
                            station,
                            key,
                            wind_dir,
                            wind_avg,
                            wind_max,
                            temperature=temp,
                            humidity=humidity,
                            pressure=Pressure(qfe=qfe, qnh=qnh, qff=qff),
                            rain=rain,
                        )
                        new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures)

                except ProviderException as e:
                    self.log.warn(f"Error while processing station '{station_id}': {e}")
                except Exception as e:
                    self.log.exception(f"Error while processing station '{station_id}': {e}")

        except Exception as e:
            self.log.exception(f'Error while processing MeteoSwiss: {e}')

        self.log.info('...Done!')


MeteoSwiss().process_data()
