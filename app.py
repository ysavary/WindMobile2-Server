import os
from flask import Flask
from flask import render_template
from flask.ext.pymongo import PyMongo

app = Flask(__name__)
app.config['MONGO_URI'] = 'mongodb://heroku_app9085441:ibtavke6ij35tahjboiioqdk2b@ds029197.mongolab.com:29197/heroku_app9085441'
mongo = PyMongo(app)

@app.route('/')
def home_page():
    stations = mongo.db.jdc_stations.find()
    return render_template('index.html', stations=stations)

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)