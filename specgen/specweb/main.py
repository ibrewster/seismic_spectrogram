import bz2
import json
import os
import pickle

from io import BytesIO
from datetime import datetime

import flask

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
from matplotlib.colors import Normalize

from . import app
from specgen import graphing
from specgen.config import locations, stations


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


@app.route('/fullImage')
def get_full_image():
    target_stations = json.loads(flask.request.args['stations'])
    volcano = flask.request.args['volcano']

    plot_path = os.path.dirname(__file__)
    static_folder = app.config.get('static_folder', 'static')
    target_date = datetime.strptime(flask.request.args['time'], '%Y-%m-%dT%H:%M:%S')
    year = str(target_date.year)
    month = str(target_date.month)
    day = str(target_date.day)
    target_filename = f"{target_date.strftime('%Y%m%dT%H%M%S')}.pbz2"

    plot_height = 1.52 * len(target_stations) + 1
    plot_width = 5.76
    num_plots = 2 * len(target_stations)
    ratios = [3, 10] * len(target_stations)
    dpi = 100

    plt.rcParams.update({'font.size': 7})
    fig = plt.figure(dpi = dpi, figsize = (plot_width, plot_height))

    gs = fig.add_gridspec(num_plots, hspace = 0, height_ratios = ratios)
    axes = gs.subplots(sharex = True)
    title = f"{volcano} {target_date.strftime('%Y-%m-%d')}"
    axes[0].set_title(title, fontsize=12, fontweight = 'bold')

    for idx, sta in enumerate(target_stations):
        plot_data_path = os.path.join(plot_path, static_folder, 'plots',
                                      sta, year, month, day, target_filename)

        ax_idx = 2 * idx
        ax1 = axes[ax_idx]
        ax2 = axes[ax_idx + 1]

        try:
            with bz2.BZ2File(plot_data_path, 'r') as figure_file:
                waveform_times = pickle.load(figure_file)
                z_data = pickle.load(figure_file)

                graphing.gen_station_subplots(waveform_times, z_data, ax1, ax2)
        except FileNotFoundError:
            station_label = f"{sta}.{stations[sta]['CHAN']}"
            graphing.configure_spectrograph_y(station_label, ax1, ax2)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    side_padding = 25 / (plot_width * dpi)
    bottom_padding = 25 / (plot_height * dpi)
    fig.tight_layout(pad = 0, rect = (side_padding, bottom_padding,
                                      1 - side_padding, 1))

    print(waveform_times)
    print(z_data)

    img = BytesIO()
    fig.savefig(img, format = "png")
    img.seek(0)

    plt.close(fig)
    return flask.send_file(img, mimetype = 'image/png')
