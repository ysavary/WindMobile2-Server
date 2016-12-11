import requests

from provider import get_logger, Provider, ProviderException
from python_metar.metar.Metar import Metar as PyMetar, ParserError
from python_metar.metar import Station

logger = get_logger('metar')


class Metar(Provider):
    provider_code = 'metar'
    provider_name = 'METAR'
    provider_url = 'http://tgftp.nws.noaa.gov/data/observations/metar/decoded/'

    def process_data(self):
        try:
            logger.info("Processing Metar station list...")

            try:
                logger.info("Processing Metar data...")
                result = requests.get("http://tgftp.nws.noaa.gov/data/observations/metar/cycles/00Z.TXT",
                                      timeout=(self.connect_timeout, self.read_timeout), stream=True)

                for line in result.iter_lines():
                    try:
                        # filter out keep-alive new lines
                        if line:
                            try:
                                obs = PyMetar(line.decode("utf-8"))
                            except ParserError:
                                continue

                            station = Station.stations[obs.station_id]
                            print("station_id : " + station.id)

                            print("time : " + str(obs.time))
                            print("cycle : " + str(obs.cycle))

                            print("wind_dir : " + str(obs.wind_dir.value()))
                            print("wind_speed : " + str(obs.wind_speed.value()))
                            print("wind_gust : " + str(obs.wind_gust.value()))



                    except ProviderException as e:
                        logger.warn("Error while processing station '{0}'".format(e))
                    except Exception as e:
                        logger.exception("Error while processing station '{0}'".format(e))
                        self.raven_client.captureException()

            except ProviderException as e:
                logger.warn("Error while processing station '{0}'".format(e))
            except Exception as e:
                logger.exception("Error while processing station '{0}'".format(e))
                self.raven_client.captureException()

        except Exception as e:
            logger.exception("Error while processing Pioupiou: {0}".format(e))
            self.raven_client.captureException()

        logger.info("Done !")


Metar().process_data()
