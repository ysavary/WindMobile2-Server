import calendar
from datetime import datetime
from pytz import timezone
import os
import json
import re

# Modules
import requests
from html5lib import HTMLParser, treebuilders

from provider import get_logger, Provider, ProviderException, Status

logger = get_logger('meteoswiss')


class MeteoSwiss(Provider):
    provider_prefix = 'meteoswiss'
    provider_name = 'meteoswiss.ch'

    def __init__(self, mongo_url):
        super(MeteoSwiss, self).__init__(mongo_url)

    def process_data(self):
        try:
            logger.info(u"Processing METEOSWISS data...")

            with open('swissmetnet.json') as in_file:
                locations = json.load(in_file)

            parser = HTMLParser(tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
            root = parser.parse(requests.get(
                "http://www.meteoswiss.admin.ch/web/en/weather/current_weather.par0013.html?allStations=1").text)

            update_tag = root.xpath('.//p[starts-with(text(),"Updated")]')[0]
            switzerland = timezone('Europe/Zurich')
            update_time = switzerland.localize(
                datetime.strptime(update_tag.text.strip(), 'Updated on %d.%m.%Y, %H.%M'))
            key = calendar.timegm(update_time.utctimetuple())

            name_pattern = re.compile(u"(?P<name>.*?) \((?P<alt>[0-9]+) m asl\)")
            wind_pattern = re.compile(u"(?P<dir>[0-9]+)\|(?P<average>[0-9]+)\|(?P<max>[0-9]+)")

            r = root.xpath("//div[@class='karte_text_hidden']")
            for element in r:
                try:
                    div_wind_id = element.attrib['id']
                    station_id = div_wind_id[-3:]
                    try:
                        station_text = root.xpath("//a[contains(@href,'" + station_id + "')]/img/@title")[0]
                    except IndexError:
                        logger.error(u"Unable to find station with id '{0}'".format(station_id))
                        continue
                    match = name_pattern.match(station_text)
                    station_name = match.group('name')
                    altitude = match.group('alt')

                    wgs84 = None
                    for location in locations:
                        if location['name'] == station_name:
                            wgs84 = location['wgs84']

                    if wgs84:
                        longitude, latitude = wgs84.split(',')
                    else:
                        logger.error(u"Unable to find wgs84 for station '{0}'".format(station_name))
                        continue

                    wind_text = root.xpath("//div[@id='" + div_wind_id + "']/span/text()")[0]
                    if not wind_text == '-|-|-':
                        status = Status.GREEN
                    else:
                        status = Status.RED

                    station = self.create_station(
                        station_id,
                        station_name,
                        station_name,
                        '',
                        ['switzerland'],
                        altitude,
                        latitude,
                        longitude,
                        status)
                    self.stations_collection().save(station)

                    if status == Status.GREEN:
                        measures_collection = self.measures_collection(station_id)
                        new_measures = []

                        match = wind_pattern.match(wind_text)
                        wind_direction = match.group('dir')
                        wind_average = match.group('average')
                        wind_maximum = match.group('max')

                        if not measures_collection.find_one(key):
                            last_measure = measures_collection.find_one({'$query': {}, '$orderby': {'_id': -1}})
                            measure = self.create_measure(
                                key,
                                wind_direction,
                                wind_average,
                                wind_maximum,
                                None,
                                None)

                            if not last_measure == measure:
                                new_measures.append(measure)
                            else:
                                logger.info(u"Same value as last measure for station '{0}'".format(station_name))

                        self.insert_new_measures(measures_collection, station, new_measures, logger)
                        self.add_last_measure(station_id)

                except (ProviderException, StandardError) as e:
                    logger.error(u"Error while processing measures for station '{0}': {1}".format(station_id, e))

        except (ProviderException, StandardError) as e:
            logger.error(u"Error while processing METEOSWISS: {0}".format(e))


meteoswiss = MeteoSwiss(os.environ['WINDMOBILE_MONGO_URL'])
meteoswiss.process_data()
