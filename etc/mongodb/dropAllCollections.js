var collectionNames = db.getCollectionNames();
for(var i = 0, len = collectionNames.length; i < len ; i++){
    var collectionName = collectionNames[i];
    if(collectionName.indexOf('system') == -1){
        db[collectionName].drop()
    }
}