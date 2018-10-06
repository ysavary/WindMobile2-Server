import codecs
import json
from collections import OrderedDict

from commons.projections import ch_to_wgs_lon, ch_to_wgs_lat

stations = OrderedDict({})
with codecs.open('VQHA69_EN.txt', encoding='iso-8859-1') as in_file:
    with open('vqha69.json', 'w') as out_file:
        lines = in_file.readlines()
        for i in range(17, 131):
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
