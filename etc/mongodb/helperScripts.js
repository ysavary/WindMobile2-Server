db.stations.find({name: 'Zinal'});

new Date(1000*1427812800);

db['jdc-1003'].find({$query: {}, $orderby: {'_id': -1}});
db['jdc-1003'].findOne({$query: {}, $orderby: {'_id': -1}});

db.stations.find({'pv-code': 'pioupiou'});
db.stations.distinct('cat');

db['meteoswiss-DOL'].find({'_id': {'$gte': new Date().getTime()/1000 - 3600}}).sort({'_id': -1}).forEach(function custom_print(doc) {print(new Date(doc._id*1000));printjson(doc);});