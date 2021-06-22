import configparser
import csv
import pprint

from collections import defaultdict
from io import StringIO

import numpy as np
import pandas
import requests

from obspy import UTCDateTime
from obspy.clients.earthworm import Client as WClient


CHANNEL_MASK = '[SB]HZ'
MAX_STATIONS = 8
MAX_AGE = 7 * 24 * 60 * 60  # 7 days

VOLCS = {
    'Wrangell': {'latitude': 62.0057, 'longitude': -144.0194, 'radius': 60},
    'Spurr': {'latitude': 61.2989, 'longitude': -152.2539, 'radius': 30},
    'Redoubt': {'latitude': 60.4852, 'longitude': -152.7438, 'radius': 30},
    'Iliamna': {'latitude': 60.0319, 'longitude': -153.0918, 'radius': 30}
}


def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)

    All args must be of equal length.

    Less precise than vincenty, but fine for short distances,
    and works on vector math

    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2

    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km


def get_meta(NET):
    args = {
        'net': NET,
        'level': 'channel',
        'format': 'text'
    }
    resp = requests.get(IRIS_URL, args)

    # Parse the delimited response
    resp_str = StringIO(resp.text)
    reader = csv.reader(resp_str, delimiter = '|')
    keys = [x.strip() for x in next(reader)]
    return {(row[1], row[3]): dict(zip(keys, row)) for row in reader}


def make_net_dict(avail, meta):
    nets = pandas.DataFrame()
    channels = defaultdict(list)
    for item in avail:
        sta = item[1]
        chan = item[3]
        last_data = item[5]
        last_data_age = (UTCDateTime() - last_data)  # in seconds
        if last_data_age > MAX_AGE:
            continue  # Data too old. Discard channel.

        sta_meta = meta.get((sta, chan))

        if not sta_meta:
            continue

        if sta not in channels:
            # Only append this to the data frame if we haven't seen it before

            item_dict = {
                'station': sta,
                'latitude': float(sta_meta['Latitude']),
                'longitude': float(sta_meta['Longitude']),
            }
            nets = nets.append(item_dict, ignore_index = True)

        chan_data = (
            chan,
            int(float(sta_meta['Scale'])),
            float(sta_meta['SampleRate'])
        )
        channels[sta].append(chan_data)

    return nets, channels


config = configparser.ConfigParser()
config.read("specgen/config.ini")

winston_url = config['WINSTON']['url']
winston_port = config['WINSTON'].getint('port', 16022)
wclient = WClient(winston_url, winston_port)

IRIS_URL = config['IRIS']['url']

av_avail = wclient.get_availability(network='AV', channel = CHANNEL_MASK)
ak_avail = wclient.get_availability(network='AK', channel = CHANNEL_MASK)

# Get metadata about the available stations
av_meta = get_meta('AV')
ak_meta = get_meta('AK')

av_nets, av_channels = make_net_dict(av_avail, av_meta)
ak_nets, ak_channels = make_net_dict(ak_avail, ak_meta)

av_nets['net'] = ['AV'] * len(av_nets)
ak_nets['net'] = ['AK'] * len(ak_nets)
all_nets = av_nets.append(ak_nets, ignore_index = True)

all_channels = dict(av_channels)
all_channels.update(ak_channels)


locations = defaultdict(list)
for volc, info in VOLCS.items():
    lat1 = info['latitude']
    lon1 = info['longitude']
    all_nets['dist'] = haversine_np(lon1, lat1, all_nets.longitude, all_nets.latitude)
    max_dist = info['radius']
    avail_nets = all_nets.loc[all_nets.dist <= max_dist]
    chosen_nets = avail_nets.sort_values('dist').head(MAX_STATIONS)
    for net in chosen_nets.itertuples():
        sta = net.station
        channels, scales, rates = zip(*all_channels[sta])
        sta_dict = {'STA': sta}

        if 'BHZ' not in channels:
            sta_dict['CHAN'] = channels[0]
            sta_dict['SCALE'] = scales[0]
            sta_dict['SAMPLE_RATE'] = rates[0]
        else:
            bhz_idx = channels.index('BHZ')
            sta_dict['SCALE'] = scales[bhz_idx]
            sta_dict['SAMPLE_RATE'] = rates[bhz_idx]

        if net.net != 'AV':
            sta_dict['NET'] = net.net

        locations[volc].append(sta_dict)

with open('specgen/station_config.py', 'w') as conf_file:
    pprinter = pprint.PrettyPrinter(stream = conf_file)
    conf_file.write('locations=')
    pprinter.pprint(dict(locations))
