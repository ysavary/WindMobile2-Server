import json
import os

import arrow
import arrow.parser
import metar
import requests
from metar.Metar import Metar

from provider import get_logger, Provider, ProviderException, Status, ureg, Q_

logger = get_logger('metar')


def warn_unparsed_group(metar, group):
    logger.warn("Unparsed '{group}'".format(group=group))


metar.Metar._unparsedGroup = warn_unparsed_group


class MetarNoaa(Provider):
    provider_code = 'metar'
    provider_name = 'noaa.gov/metar'
    provider_url = 'http://aviationweather.cp.ncep.noaa.gov/metar/'

    direction_units = {
        'degree': ureg.degree,
    }

    speed_units = {
        'KT': ureg.knot,
        'MPS': ureg.meter / ureg.second,
        'KMH': ureg.kilometer / ureg.hour,
        'MPH': ureg.mile / ureg.hour
    }

    temperature_units = {
        'F': ureg.degF,
        'C': ureg.degC,
        'K': ureg.degK
    }

    pressure_units = {
        'MB': ureg.Pa,
        'HPA': ureg.Pa * 100,
        'IN': ureg.in_Hg
    }

    def get_quantity(self, measure, units):
        if measure:
            return Q_(measure._value, units[measure._units])

    def get_direction(self, measure):
        if measure:
            return Q_(measure._degrees, self.direction_units['degree'])

    def process_data(self):
        try:
            logger.info('Processing Metar data...')

            with open(os.path.join(os.path.dirname(__file__), 'metar/icao.json')) as in_file:
                icao = json.load(in_file)

            hour = arrow.utcnow().hour
            minute = arrow.utcnow().minute

            if minute < 45:
                current_cycle = hour
            else:
                current_cycle = hour + 1 % 24

            stations = {}
            for cycle in (current_cycle-1, current_cycle):
                file = 'http://tgftp.nws.noaa.gov/data/observations/metar/cycles/{cycle:02d}Z.TXT'.format(
                    cycle=cycle)
                logger.info("Processing '{file}' ...".format(file=file))

                request = requests.get(file, stream=True, timeout=(self.connect_timeout, self.read_timeout))
                for line in request.iter_lines():
                    if line:
                        try:
                            data = line.decode('iso-8859-1')
                            # Is this line a date with format "2017/05/12 23:55" ?
                            arrow.get(data, 'YYYY/MM/DD HH:mm')
                            continue
                        except arrow.parser.ParserError:
                            try:
                                metar = Metar(data)
                                if metar.wind_dir and metar.wind_speed:
                                    if metar.station_id not in stations:
                                        stations[metar.station_id] = {}
                                    key = arrow.get(metar.time).timestamp
                                    stations[metar.station_id][key] = metar
                            except Exception as e:
                                logger.warn('Error while parsing METAR data: {e}'.format(e=e))
                                continue

            for metar_id in stations:
                metar = next(iter(stations[metar_id].values()))
                try:
                    lat, lon = None, None
                    if metar.station_id in icao:
                        lat = icao[metar.station_id]['lat']
                        lon = icao[metar.station_id]['lon']
                    if not lat and not lon:
                        lat, lon = None, None

                    station = self.save_station(
                        metar.station_id,
                        None,
                        None,
                        lat,
                        lon,
                        Status.GREEN,
                        url=os.path.join(self.provider_url, 'site?id={id}&db=metar'.format(id=metar.station_id)),
                        default_name='{icao} Airport'.format(icao=metar.station_id),
                        lookup_name='{icao} Airport ICAO'.format(icao=metar.station_id))
                    station_id = station['_id']

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []
                    for key in stations[metar_id]:
                        metar = stations[metar_id][key]
                        if not self.has_measure(measures_collection, key):
                            measure = self.create_measure(
                                key,
                                self.get_direction(metar.wind_dir),
                                self.get_quantity(metar.wind_speed, self.speed_units),
                                self.get_quantity(metar.wind_gust or metar.wind_speed, self.speed_units),
                                temperature=self.get_quantity(metar.temp, self.temperature_units),
                                humidity=None,
                                pressure=self.get_quantity(metar.press, self.pressure_units),
                                luminosity=None,
                                rain=None)
                            new_measures.append(measure)

                    self.insert_new_measures(measures_collection, station, new_measures, logger)

                except ProviderException as e:
                    logger.warn("Error while processing station '{id}': {e}".format(id=metar_id, e=e))
                except Exception as e:
                    logger.exception("Error while processing station '{id}': {e}".format(id=metar_id, e=e))
                    self.raven_client.captureException()

        except Exception as e:
            logger.exception('Error while processing Metar: {e}'.format(e=e))
            self.raven_client.captureException()

        logger.info('Done !')


MetarNoaa().process_data()
