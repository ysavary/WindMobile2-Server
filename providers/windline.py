from datetime import datetime, timedelta
from urllib.parse import urlparse

import MySQLdb
import arrow
from cachetools import hashkey, cached

import wgs84
from provider import get_logger, Provider, ProviderException, Status
from settings import *

logger = get_logger('windline')


class NoMeasure(Exception):
    pass


class Windline(Provider):
    provider_code = 'windline'
    provider_name = 'windline.ch'
    provider_url = 'http://www.windline.ch'

    # status_property_id = get_property_id('status')
    status_property_id = 13
    # altitude_property_id = get_property_id('altitude')
    altitude_property_id = 9
    # longitude_property_id = get_property_id('longitude')
    longitude_property_id = 16
    # latitude_property_id = get_property_id('latitude')
    latitude_property_id = 17

    wind_average_type = 16402
    wind_maximum_type = 16410
    wind_direction_type = 16404
    temperature_type = 16400
    humidity_type = 16401

    def __init__(self):
        super().__init__()
        self.windline_url = WINDLINE_URL

    # Windline status: offline, maintenance, demo or online
    def get_status(self, status):
        if status == 'offline':
            return Status.HIDDEN
        elif status == 'maintenance':
            return Status.RED
        elif status == 'demo':
            return Status.ORANGE
        elif status == 'online':
            return Status.GREEN
        else:
            return Status.HIDDEN

    def get_property_id(self, cursor, key):
        cursor.execute("SELECT tblstationpropertylistno FROM tblstationpropertylist WHERE uniquename=%s", (key,))
        try:
            return cursor.fetchone()[0]
        except TypeError:
            raise ProviderException("No property '{0}'".format(key))

    def get_property_value(self, cursor, station_no, property_id):
        cursor.execute(
            "SELECT value FROM tblstationproperty WHERE tblstationno=%s AND tblstationpropertylistno=%s",
            (station_no, property_id))
        try:
            return cursor.fetchone()[0]
        except TypeError:
            raise ProviderException("No property value for property '{0}'".format(property_id))

    def get_measures(self, cursor, station_id, data_id, start_date):
        cursor.execute("""SELECT measuredate, data FROM tblstationdata
            WHERE stationid=%s AND dataid=%s AND measuredate>=%s
            ORDER BY measuredate""", (station_id, data_id, start_date))
        return cursor.fetchall()

    @cached(cache={}, key=lambda self, cursor, station_no, data_id: hashkey(station_no, data_id))
    def get_measure_correction(self, cursor, station_no, data_id):
        try:
            cursor.execute(
                """SELECT onlyvalue FROM tblcalibrate WHERE tblstationno=%s AND tbldatatypeno=("""
                """    SELECT tbldatatypeno FROM tbldatatype WHERE dataid=%s"""
                """)""", (station_no, data_id))
            return cursor.fetchone()[0]
        except (TypeError, ValueError):
            return None

    def get_corrected_value(self, cursor, value, station_no, data_id):
        correction = self.get_measure_correction(cursor, station_no, data_id)
        if correction:
            if data_id == self.wind_direction_type:
                return (value + correction) % 360
            else:
                return value + correction
        return value

    def get_measure_value(self, rows, start_date, end_date):
        for row in reversed(rows):
            date = row[0]
            if start_date <= date <= end_date:
                return float(row[1])
        raise NoMeasure()

    def get_last_measure_value(self, rows, end_date):
        for row in reversed(rows):
            date = row[0]
            if date <= end_date:
                return float(row[1])
        raise NoMeasure()

    def ms_to_kmh(self, value):
        return float(value) * 3.6

    def process_data(self):
        try:
            logger.info("Processing WINDLINE data...")

            connection_info = urlparse(self.windline_url)
            mysql_connection = MySQLdb.connect(connection_info.hostname, connection_info.username,
                                               connection_info.password, connection_info.path[1:], charset='utf8')

            # mysql_connection is buffered by default so we can use the same cursor with fetchall
            mysql_cursor = mysql_connection.cursor()

            start_date = datetime.utcnow() - timedelta(days=2)

            # Fetch only stations that have a status (property_id=13)
            mysql_cursor.execute("""SELECT tblstation.tblstationno, stationid, stationname, shortdescription, value
                FROM tblstation
                INNER JOIN tblstationproperty
                ON tblstation.tblstationno = tblstationproperty.tblstationno
                WHERE tblstationpropertylistno=%s""", (self.status_property_id,))
            for row in mysql_cursor.fetchall():
                station_no = row[0]
                windline_id = row[1]
                short_name = row[2]
                name = row[3]
                status = row[4]

                station_id = None
                try:
                    station_id = self.get_station_id(windline_id)
                    station = self.save_station(
                        station_id,
                        short_name,
                        name,
                        wgs84.parse_dms(self.get_property_value(mysql_cursor, station_no, self.latitude_property_id)),
                        wgs84.parse_dms(self.get_property_value(mysql_cursor, station_no, self.longitude_property_id)),
                        self.get_status(status),
                        altitude=self.get_property_value(mysql_cursor, station_no, self.altitude_property_id))

                    try:
                        measures_collection = self.measures_collection(station_id)
                        new_measures = []

                        wind_average_rows = self.get_measures(
                            mysql_cursor, windline_id, self.wind_average_type, start_date)
                        wind_maximum_rows = self.get_measures(
                            mysql_cursor, windline_id, self.wind_maximum_type, start_date)
                        wind_direction_rows = self.get_measures(
                            mysql_cursor, windline_id, self.wind_direction_type, start_date)
                        temperature_rows = self.get_measures(
                            mysql_cursor, windline_id, self.temperature_type, start_date)
                        humidity_rows = self.get_measures(
                            mysql_cursor, windline_id, self.humidity_type, start_date)

                        # The wind average measure is the time reference for a measure
                        for wind_average_row in wind_average_rows:
                            try:
                                key = arrow.get(wind_average_row[0]).timestamp
                                if key not in [measure['_id'] for measure in new_measures] and \
                                        not measures_collection.find_one(key):
                                    wind_average = self.ms_to_kmh(wind_average_row[1])

                                    measure_date = wind_average_row[0]

                                    wind_maximum = self.ms_to_kmh(self.get_measure_value(
                                        wind_maximum_rows,
                                        measure_date - timedelta(seconds=10), measure_date + timedelta(seconds=10)))

                                    wind_direction = self.get_measure_value(
                                        wind_direction_rows,
                                        measure_date - timedelta(seconds=10), measure_date + timedelta(seconds=10))
                                    wind_direction = self.get_corrected_value(mysql_cursor, wind_direction, station_no,
                                                                              self.wind_direction_type)

                                    temperature = self.get_last_measure_value(
                                        temperature_rows,
                                        measure_date + timedelta(seconds=10))

                                    humidity = self.get_last_measure_value(
                                        humidity_rows,
                                        measure_date + timedelta(seconds=10))

                                    measure = self.create_measure(
                                        key,
                                        wind_direction,
                                        wind_average,
                                        wind_maximum,
                                        temperature,
                                        humidity)
                                    new_measures.append(measure)
                            except NoMeasure:
                                pass

                        self.insert_new_measures(measures_collection, station, new_measures, logger)

                    except Exception as e:
                        logger.exception("Error while processing measures for station '{0}': {1}".format(station_id, e))

                    self.add_last_measure(station_id)

                except Exception as e:
                    logger.error("Error while processing station '{0}': {1}".format(station_id, e))

        except Exception as e:
            logger.error("Error while processing Windline: {0}".format(e))
        finally:
            mysql_cursor.close()
            mysql_connection.close()

        logger.info("Done !")

Windline().process_data()
