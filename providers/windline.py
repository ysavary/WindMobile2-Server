import os
from urlparse import urlparse
from datetime import datetime, timedelta
import calendar

# Modules
import pymongo
#import mysql.connector
import MySQLdb

import provider
import wgs84

logger = provider.get_logger('windline')

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
            "SELECT value FROM tblstationproperty WHERE tblstationno=%s AND tblstationpropertylistno=%s", (station_no, property_id))
        return cursor.fetchone()[0]


    def get_historic_measures(self, cursor, station_id, data_id, start_date):
        cursor.execute(
            "SELECT measuredate, data FROM tblstationdata WHERE stationid=%s AND dataid=%s AND measuredate>%s ORDER BY measuredate",
            (station_id, data_id, start_date))
        return cursor.fetchall()


    def add_measure(self, windline_dict, unix_time, measure_name, measure_value):
        key = round(unix_time, -1)
        if not key in windline_dict:
            windline_dict[key] = {measure_name: measure_value}
        else:
            measures = windline_dict[key]
            measures[measure_name] = measure_value
            windline_dict[key] = measures

    def process_data(self):
        try:
            logger.info("Processing WINDLINE data...")

            logger.info("Connecting to '{0}'".format(self.windline_url))
            connection_info = urlparse(self.windline_url)
            mysql_connection = MySQLdb.connect(connection_info.hostname, connection_info.username, connection_info.password,
                connection_info.path[1:], charset='utf8')
            # Cannot leave cursors open with module 'mysql-connector-python': the loops are too long (db connection timeout) and it's too slow
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

            wind_direction_type = 16404
            wind_average_type = 16402
            wind_maximum_type = 16410
            temperature_type = 16400
            humidity_type = 16401

            historic_start_date = datetime.utcnow() - timedelta(days=2)
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
                               'longitude': wgs84.parse_dms(self.get_property_value(mysql_cursor, station_no, longitude_property_id)),
                               'latitude': wgs84.parse_dms(self.get_property_value(mysql_cursor, station_no, latitude_property_id)),
                               'status': self.get_status(status),
                    }
                    self.stations_collection.insert(station)

                    try:
                        try:
                            kwargs = {'capped': True, 'size': 500000, 'max': 5000}
                            values_collection = self.mongo_db.create_collection(station_id, **kwargs)
                        except pymongo.errors.CollectionInvalid:
                            values_collection = self.mongo_db[station_id]

                        windline_dict = {}

                        # Wind direction
                        for row in self.get_historic_measures(mysql_cursor, windline_id, wind_direction_type, historic_start_date):
                            date = row[0]
                            value = row[1]
                            unix_time = calendar.timegm(date.timetuple())
                            self.add_measure(windline_dict, unix_time, 'wind-direction', float(value))

                        for row in self.get_historic_measures(mysql_cursor, windline_id, wind_average_type, historic_start_date):
                            date = row[0]
                            value = row[1]
                            unix_time = calendar.timegm(date.timetuple())
                            self.add_measure(windline_dict, unix_time, 'wind-average', float(value))

                        for row in self.get_historic_measures(mysql_cursor, windline_id, wind_maximum_type, historic_start_date):
                            date = row[0]
                            value = row[1]
                            unix_time = calendar.timegm(date.timetuple())
                            self.add_measure(windline_dict, unix_time, 'wind-maximum', float(value))

                        for row in self.get_historic_measures(mysql_cursor, windline_id, temperature_type, historic_start_date):
                            date = row[0]
                            value = row[1]
                            unix_time = calendar.timegm(date.timetuple())
                            self.add_measure(windline_dict, unix_time, 'temperature', float(value))

                        for row in self.get_historic_measures(mysql_cursor, windline_id, humidity_type, historic_start_date):
                            date = row[0]
                            value = row[1]
                            unix_time = calendar.timegm(date.timetuple())
                            self.add_measure(windline_dict, unix_time, 'humidity', float(value))

                        new_measures = []
                        for key in sorted(windline_dict.keys()):
                            if not values_collection.find_one(key):
                                measures = windline_dict[key]
                                measures['_id'] = key
                                values_collection.insert(measures)
                                new_measures.append(measures)

                        if len(new_measures) > 0:
                            start_date = datetime.fromtimestamp(new_measures[0]['_id'])
                            end_date = datetime.fromtimestamp(new_measures[-1]['_id'])
                            logger.info(
                                "--> from " + start_date.strftime('%Y-%m-%dT%H:%M:%S') + " to " + end_date.strftime('%Y-%m-%dT%H:%M:%S') + ", " +
                                station['short-name'] + " (" + station_id + "): " + str(len(new_measures)) + " values inserted")

                    except Exception as e:
                        logger.exception("Error while fetching data for station '{0}':".format(station_id))

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