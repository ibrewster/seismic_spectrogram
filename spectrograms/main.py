import os
import importlib

import flask
from . import app


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route('/locations')
def get_locations():
    file_path = os.path.dirname(__file__)
    conf_path = os.path.realpath(os.path.join(file_path, '../station_config.py'))
    if not os.path.isfile(conf_path):
        raise flask.abort(404)

    spec = importlib.util.spec_from_file_location("station_config", conf_path)
    conf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conf)

    locations = conf.locations
    return flask.jsonify(tuple(locations.keys()))
