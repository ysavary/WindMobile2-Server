db.stations.find({ loc: { $geoWithin: { $geometry: { type: "Polygon", coordinates: [ [ [ 3.821490435937449, 45.52096247389434 ], [ 2.882159381249949, 45.52096247389434 ], [ 2.882159381249949, 45.1302123318299 ], [ 3.821490435937449, 45.1302123318299 ], [ 3.821490435937449, 45.52096247389434 ] ] ], crs: { type: "name", properties: { name: "urn:x-mongodb:crs:strictwinding:EPSG:4326" } } } } }, status: { $ne: "hidden" } }).explain()

db.stations.find({ 'pv-code': "jdc", loc: { $geoWithin: { $geometry: { type: "Polygon", coordinates: [ [ [ 10.39674111875001, 48.25623531802949 ], [ 2.882092681250015, 48.25623531802949 ], [ 2.882092681250015, 45.13023548426339 ], [ 10.39674111875001, 45.13023548426339 ], [ 10.39674111875001, 48.25623531802949 ] ] ], crs: { type: "name", properties: { name: "urn:x-mongodb:crs:strictwinding:EPSG:4326" } } } } }, status: { $ne: "hidden" } }).explain()

db.stations.find({ loc: { $near: { $geometry: { type: "Point", coordinates: [ 6.6394803, 46.7158458 ] } } }, status: { $ne: "hidden" } }).explain()

db.stations.find({ 'pv-code': "jdc", loc: { $near: { $geometry: { type: "Point", coordinates: [ 6.6394803, 46.7158458 ] } } }, status: { $ne: "hidden" } }).explain()
