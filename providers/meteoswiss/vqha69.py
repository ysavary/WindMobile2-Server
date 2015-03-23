# coding=utf-8
from __future__ import division
import codecs
import json
import math


def dm_to_dd(s):
    d, m = s.split(u'°')
    dd = float(d) + float(m.strip()[:-1]) / 60
    return dd


def ch_to_wgs_lat(y, x):
    """Convert CH y/x to WGS lat"""

    # Converts military to civil and  to unit = 1000km
    # Auxiliary values (% Bern)
    y_aux = (y - 600000)/1000000
    x_aux = (x - 200000)/1000000

    # Process lat
    lat = 16.9023892 \
        + 3.238272 * x_aux \
        - 0.270978 * math.pow(y_aux, 2) \
        - 0.002528 * math.pow(x_aux, 2) \
        - 0.0447   * math.pow(y_aux, 2) * x_aux \
        - 0.0140   * math.pow(x_aux, 3)

    # Unit 10000" to 1 " and converts seconds to degrees (dec)
    lat = lat * 100/36
    return lat


def ch_to_wgs_lon(y, x):
    """Convert CH y/x to WGS long"""

    # Converts military to civil and  to unit = 1000km
    # Auxiliary values (% Bern)
    y_aux = (y - 600000)/1000000
    x_aux = (x - 200000)/1000000

    # Process long
    lon = 2.6779094 \
        + 4.728982 * y_aux \
        + 0.791484 * y_aux * x_aux \
        + 0.1306   * y_aux * math.pow(x_aux, 2) \
        - 0.0436   * math.pow(y_aux, 3)

    # Unit 10000" to 1 " and converts seconds to degrees (dec)
    lon = lon * 100/36
    return lon


stations = {}
with codecs.open('VQHA69_EN.txt', encoding='iso-8859-1') as in_file:
    with open('vqha69.json', 'w') as out_file:
        lines = in_file.readlines()
        for i in range(17, 130):
            lon, lat = lines[i][50:63].split('/')
            station = {
                'name': lines[i][25:50].strip(),
                'altitude': int(lines[i][100:104]),
                'location': {
                    'lon': ch_to_wgs_lon(int(lines[i][75:81]), int(lines[i][82:88])),
                    'lat': ch_to_wgs_lat(int(lines[i][75:81]), int(lines[i][82:88]))
                }
            }
            stations[lines[i][0:3]] = station
        json.dump(stations, out_file)