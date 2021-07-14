import flask
from . import app
from specgen import graphing
from specgen.config import locations


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route('/locations')
def get_locations():
    locs_order = sorted(locations.keys(), key = lambda x: locations[x]['sort'],
                        reverse = True)
    locs_stations = {key: value['stations']
                     for key, value in locations.items()}

    ret_obj = {'locations': tuple(locs_order),
               'loc_stations': locs_stations}

    return flask.jsonify(ret_obj)
