import json
import math
import os
from random import randint

import arrow
import arrow.parser
import metar
import requests
from metar.Metar import Metar

from provider import get_logger, Provider, ProviderException, Status, ureg, Q_, UsageLimitException
from settings import CHECKWX_API_KEY

logger = get_logger('metar')


def warn_unparsed_group(metar, group):
    logger.warn("'{code}': unparsed group '{group}'".format(code=metar.code, group=group['group']))


metar.Metar._unparsedGroup = warn_unparsed_group


class MetarNoaa(Provider):
    provider_code = 'metar'
    provider_name = 'noaa.gov/metar'
    provider_url = 'http://aviationweather.cp.ncep.noaa.gov/metar/'

    def __init__(self):
        super().__init__()
        self.checkwx_api_key = CHECKWX_API_KEY

    @property
    def checkwx_cache_duration(self):
        return (30 + randint(-2, 2)) * 24 * 3600

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
        else:
            # For VaRiaBle direction, use a random value
            return Q_(randint(0, 359), self.direction_units['degree'])

    def compute_humidity(self, dew_point, temp):
        if not (dew_point and temp):
            return None

        a = 17.625
        b = 243.04
        td = dew_point.to(ureg.degC).magnitude
        t = temp.to(ureg.degC).magnitude

        return 100 * (math.exp((a * td) / (b + td))) / (math.exp((a * t) / (b + t)))

    def process_data(self):
        try:
            logger.info('Processing Metar data...')

            with open(os.path.join(os.path.dirname(__file__), 'metar/stations.json')) as in_file:
                icao = json.load(in_file)

            now = arrow.utcnow()
            hour = now.hour
            minute = now.minute

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
                            try:
                                arrow.get(data, 'YYYY/MM/DD HH:mm')
                            except ValueError:
                                pass
                            continue
                        except arrow.parser.ParserError:
                            try:
                                metar = Metar(data)
                                # wind_dir could be NONE if 'dir' is 'VRB'
                                if metar.wind_speed:
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
                    name, short_name, default_name, lat, lon, altitude, tz = None, None, None, None, None, None, None

                    checkwx_key = 'metar/checkwx/{icao}'.format(icao=metar.station_id)
                    if not self.redis.exists(checkwx_key):
                        try:
                            logger.info('Calling api.checkwx.com...')
                            request = requests.get(
                                'https://api.checkwx.com/station/{icao}'.format(icao=metar.station_id),
                                headers={'Accept': 'application/json', 'X-API-Key': self.checkwx_api_key},
                                timeout=(self.connect_timeout, self.read_timeout))

                            try:
                                checkwx_data = request.json()['data'][0]
                                # check if the json is a valid response
                                checkwx_data['icao']
                            except Exception:
                                messages = []
                                try:
                                    checkwx_json = request.json()
                                    if 'data' in checkwx_json:
                                        if type(checkwx_json['data']) is list:
                                            messages.extend(checkwx_json['data'])
                                        else:
                                            messages.append(checkwx_json['data'])
                                except ValueError:
                                    pass
                                raise ProviderException('CheckWX API error: {message}'.format(message=','.join(messages)))

                            self.add_redis_key(checkwx_key, {
                                'data': json.dumps(checkwx_data)
                            }, self.checkwx_cache_duration)
                        except TimeoutError as e:
                            raise e
                        except UsageLimitException as e:
                            self.add_redis_key(checkwx_key, {
                                'error': repr(e)
                            }, self.usage_limit_cache_duration)
                        except Exception as e:
                            logger.exception('Error while getting CheckWX data')
                            if not isinstance(e, ProviderException):
                                self.raven_client.captureException()
                            self.add_redis_key(checkwx_key, {
                                'error': repr(e)
                            }, self.checkwx_cache_duration)

                    if not self.redis.hexists(checkwx_key, 'error'):
                        checkwx_data = json.loads(self.redis.hget(checkwx_key, 'data'))
                        station_type = checkwx_data['type']

                        name = '{name} {type}'.format(name=checkwx_data['name'], type=station_type)
                        city = checkwx_data['city']
                        if city:
                            short_name = '{city} {type}'.format(city=city, type=station_type)
                        else:
                            default_name = checkwx_data['name']
                        lat = checkwx_data['latitude']['decimal']
                        lon = checkwx_data['longitude']['decimal']
                        tz = checkwx_data['timezone']['tzid']
                        feet = checkwx_data['elevation']['feet']
                        altitude = Q_(feet, ureg.feet) if feet else None

                    if metar.station_id in icao:
                        lat = lat or icao[metar.station_id]['lat']
                        lon = lon or icao[metar.station_id]['lon']
                        default_name = default_name or icao[metar.station_id]['name']

                    station = self.save_station(
                        metar.station_id,
                        short_name,
                        name,
                        lat,
                        lon,
                        Status.GREEN,
                        altitude=altitude,
                        tz=tz,
                        url=os.path.join(self.provider_url, 'site?id={id}&db=metar'.format(id=metar.station_id)),
                        default_name=default_name or '{icao} Airport'.format(icao=metar.station_id),
                        lookup_name='{icao} Airport ICAO'.format(icao=metar.station_id))
                    station_id = station['_id']

                    if metar.station_id not in icao:
                        logger.warn("Missing '{icao}' ICAO in database. Is it '{name}'?".format(icao=metar.station_id,
                                                                                                name=station['name']))

                    measures_collection = self.measures_collection(station_id)
                    new_measures = []
                    for key in stations[metar_id]:
                        metar = stations[metar_id][key]
                        if not self.has_measure(measures_collection, key):
                            temp = self.get_quantity(metar.temp, self.temperature_units)
                            dew_point = self.get_quantity(metar.dewpt, self.temperature_units)
                            humidity = self.compute_humidity(dew_point, temp)
                            measure = self.create_measure(
                                key,
                                self.get_direction(metar.wind_dir),
                                self.get_quantity(metar.wind_speed, self.speed_units),
                                self.get_quantity(metar.wind_gust or metar.wind_speed, self.speed_units),
                                temperature=temp,
                                humidity=humidity,
                                pressure=self.get_quantity(metar.press, self.pressure_units),
                            )
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
