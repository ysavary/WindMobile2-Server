import json

stations = {}
with open('GlobalAirportDatabase.txt', encoding='ascii') as in_file:
    with open('icao.json', 'w') as out_file:
        for line in in_file.readlines():
            values = line.strip().split(':')
            stations[values[0]] = {
                'lat': float(values[14]),
                'lon': float(values[15])
            }
        json.dump(stations, out_file)
