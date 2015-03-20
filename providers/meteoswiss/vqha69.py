# coding=utf-8
import codecs
import json


def dm_to_dd(s):
    d, m = s.split(u'°')
    dd = float(d) + float(m.strip()[:-1]) / 60
    return dd

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
                    'long': dm_to_dd(lon),
                    'lat': dm_to_dd(lat)
                }
                #'swiss_grid': lines[i][75:88]
            }
            stations[lines[i][0:3]] = station
        json.dump(stations, out_file)