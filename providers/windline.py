import os
from urlparse import urlparse
from datetime import datetime, timedelta
import calendar

# Modules
#import mysql.connector
import MySQLdb

import provider
import wgs84

logger = provider.get_logger('windline')


class NoMeasure(Exception):
    pass


class Windline(provider.Provider):
    provider_prefix = 'windline'
    provider_name = 'windline.ch'

    def __init__(self, mongo_url, windline_url):
        super(Windline, self).__init__(mongo_url)
        self.windline_url = windline_url

    # Windline status: offline, maintenance, demo or online
    def get_status(self, status):
        if status == 'offline':
            return 'hidden'
        elif status == 'maintenance':
            return 'red'
        elif status == 'demo':
            return 'orange'
        elif status == 'online':
            return 'green'
        else:
            return "hidden"

    def get_property_id(self, cursor, key):
        cursor.execute("SELECT tblstationpropertylistno FROM tblstationpropertylist WHERE uniquename=%s", (key,))
        return cursor.fetchone()[0]

    def get_property_value(self, cursor, station_no, property_id):
        cursor.execute(
            "SELECT value FROM tblstationproperty WHERE tblstationno=%s AND tblstationpropertylistno=%s",
            (station_no, property_id))
        return cursor.fetchone()[0]

    def get_measures(self, cursor, station_id, data_id, start_date):
        cursor.execute("""SELECT measuredate, data FROM tblstationdata
            WHERE stationid=%s AND dataid=%s AND measuredate>=%s
            ORDER BY measuredate""", (station_id, data_id, start_date))
        return cursor.fetchall()

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
        logger.info("get_last_measure_value: {0} {1}".format(date, end_date))
        raise NoMeasure()

    def to_wind_value(self, value):
        return round(float(value) * 3.6, 1)

    def process_data(self):
        try:
            logger.info("Processing WINDLINE data...")

            logger.info("Connecting to '{0}'".format(self.windline_url))
            connection_info = urlparse(self.windline_url)
            mysql_connection = MySQLdb.connect(connection_info.hostname, connection_info.username,
                                               connection_info.password, connection_info.path[1:], charset='utf8')

            # Cannot leave cursors open with module 'mysql-connector-python':
            # the loops are too long (db connection timeout) and it's too slow
            # Module 'mysql-python' is buffered by default so we can use the same cursor with fetchall
            mysql_cursor = mysql_connection.cursor()

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

            start_date = datetime.utcnow() - timedelta(days=2)
            self.clean_stations_collection()

            # Fetch only stations that have a status (property_id=13)
            mysql_cursor.execute("""SELECT tblstation.tblstationno, stationid, stationname, shortdescription, value
                FROM tblstation
                INNER JOIN tblstationproperty
                ON tblstation.tblstationno = tblstationproperty.tblstationno
                WHERE tblstationpropertylistno=%s""", (status_property_id,))
            for row in mysql_cursor.fetchall():
                station_no = row[0]
                windline_id = row[1]
                short_name = row[2]
                name = row[3]
                status = row[4]
                try:
                    station_id = self.get_station_id(windline_id)
                    station = {'_id': station_id,
                               'provider': self.provider_name,
                               'short-name': short_name,
                               'name': name,
                               'category': 'paragliding',
                               'tags': ['switzerland'],
                               'altitude': int(self.get_property_value(mysql_cursor, station_no, altitude_property_id)),
                               'longitude': wgs84.parse_dms(self.get_property_value(mysql_cursor, station_no,
                                                                                    longitude_property_id)),
                               'latitude': wgs84.parse_dms(self.get_property_value(mysql_cursor, station_no,
                                                                                   latitude_property_id)),
                               'status': self.get_status(status),
                    }
                    self.stations_collection.insert(station)

                    try:
                        measures_collection = self.get_or_create_measures_collection(station_id)
                        new_measures = []

                        wind_average_rows = self.get_measures(
                            mysql_cursor, windline_id, wind_average_type, start_date)
                        wind_maximum_rows = self.get_measures(
                            mysql_cursor, windline_id, wind_maximum_type, start_date)
                        wind_direction_rows = self.get_measures(
                            mysql_cursor, windline_id, wind_direction_type, start_date)
                        temperature_rows = self.get_measures(
                            mysql_cursor, windline_id, temperature_type, start_date)
                        humidity_rows = self.get_measures(
                            mysql_cursor, windline_id, humidity_type, start_date)

                        # The wind average measure is the time reference for a measure
                        for row in wind_average_rows:
                            try:
                                key = calendar.timegm(row[0].timetuple())
                                if not measures_collection.find_one(key):
                                    measure = {'_id': key,
                                               'wind-average': self.to_wind_value(row[1])}

                                    measure_date = row[0]

                                    wind_maximum = self.get_measure_value(
                                        wind_maximum_rows,
                                        measure_date - timedelta(seconds=10), measure_date + timedelta(seconds=10))
                                    measure['wind-maximum'] = self.to_wind_value(wind_maximum)

                                    wind_direction = self.get_measure_value(
                                        wind_direction_rows,
                                        measure_date - timedelta(seconds=10), measure_date + timedelta(seconds=10))
                                    measure['wind-direction'] = wind_direction

                                    temperature = self.get_last_measure_value(
                                        temperature_rows,
                                        measure_date + timedelta(seconds=10))
                                    measure['temperature'] = temperature

                                    humidity = self.get_last_measure_value(
                                        humidity_rows,
                                        measure_date + timedelta(seconds=10))
                                    measure['humidity'] = humidity

                                    new_measures.append(measure)
                            except NoMeasure:
                                pass

                        self.insert_new_measures(measures_collection, station, new_measures, logger)

                    except Exception as e:
                        logger.exception("Error while fetching data for station '{0}':".format(station_id))

                    self.add_last_measure(station_id)

                except Exception as e:
                    logger.exception("Error while processing station '{0}':".format(station_id))


        except Exception as e:
            logger.exception("Error while fetching WINDLINE data:")
        finally:
            try:
                mysql_cursor.close()
                mysql_connection.close()
            except:
                pass

windline = Windline(os.environ['WINDMOBILE_MONGO_URL'], os.environ['WINDMOBILE_WINDLINE_URL'])
windline.process_data()