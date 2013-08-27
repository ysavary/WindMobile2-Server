import json
from lxml import etree

in_file = open('swissmetnet.kml')
root = etree.parse(in_file)

stations = []

placemarks = root.xpath('//n:Placemark', namespaces={'n': 'http://www.opengis.net/kml/2.2'})
for placemark in placemarks:
    station = {
        'name': placemark.xpath('n:name', namespaces={'n': 'http://www.opengis.net/kml/2.2'})[0].text,
        'wgs84': placemark.xpath('n:Point/n:coordinates', namespaces={'n': 'http://www.opengis.net/kml/2.2'})[0].text
    }
    stations.append(station)

with open('swissmetnet.json', 'w') as out_file:
    json.dump(stations, out_file)