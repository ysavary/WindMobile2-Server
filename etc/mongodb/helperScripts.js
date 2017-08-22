db.stations.find({name: 'Zinal'});

new Date(1000*1427812800);

db['jdc-1003'].find({$query: {}, $orderby: {'_id': -1}});
db['jdc-1003'].findOne({$query: {}, $orderby: {'_id': -1}});

db.stations.find({'pv-code': 'pioupiou'}, {'short':1, 'name':1});
db.stations.distinct('cat');

db['windline-4116'].find({'_id': {'$lte': new Date('2017-06-10T00:00:00+02:00').getTime() / 1000}}).sort({'_id': -1}).limit(5).forEach(function custom_print(doc) {
    print(new Date(doc._id * 1000));
    printjson(doc);
});