import configparser
import csv
import pprint

from collections import defaultdict
from io import StringIO

import numpy as np
import pandas
import pymysql  # To get volcano names
import requests

from obspy import UTCDateTime
from obspy.clients.earthworm import Client as WClient

####################################################
#  User editable options for the station configuration
#
# Change values below to set the parameters used when
# generating the station config file
####################################################
CHANNEL_MASK = '[SB]HZ'
NETWORKS = ['AV', 'AK']
MAX_STATIONS = 5
MAX_AGE = 1 * 24 * 60 * 60  # 1 days
DEFAULT_RADIUS = 150

# Dictionary of volcanos to look at, and the radius
# around them to search for active stations.
# If latitude and longitude is specified,
# it will be used, otherwise we will try to pull latitude/longitude information
# from the database specified in the config.

VOLCS = {
    'Wrangell': {},
    'Spurr': {},
    'Redoubt': {},
    'Iliamna': {},
    'Augustine': {},
    'Fourpeaked': {},
    'Katmai Region': {'latitude': 58.2790, 'longitude': -154.9533, 'radius': 100},
    'Peulik': {},
    'Aniakchak': {},
    'Veniaminof': {},
    'Pavlof': {},
    'Dutton': {},
    'Shishaldin': {},
    'Westdahl': {},
    'Akutan': {},
    'Makushin': {},
    'Okmok': {},
    'Cleveland': {},
    'Korovin': {},
    'Great Sitkin': {},
    'Kanaga': {},
    'Tanaga': {},
    'Gareloi': {},
    'Semisopochnoi': {},
    'Little Sitkin': {},
    'Kantishna': {'latitude': 63.4000, 'longitude': -151.2000, 'radius': 160},
    'Susitna': {'latitude': 62.8295, 'longitude': -148.5509, 'radius': 160},
    'PrinceWmSn': {'latitude': 61.0400, 'longitude': -147.7300, 'radius': 160}
}

##########################################################
# END USER SETTINGS
##########################################################


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


def get_meta(NET, config):
    args = {
        'net': NET,
        'level': 'channel',
        'format': 'text'
    }

    IRIS_URL = config['IRIS']['url']

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


def generate_stations():
    config = configparser.ConfigParser()
    config.read("specgen/config.ini")

    # Get volcano locations
    DB_HOST = config['MySQL']['db_host']
    DB_USER = config['MySQL']['db_user']
    DB_PASS = config['MySQL']['db_password']
    DB_NAME = config['MySQL']['db_name']

    VOLCS_NEEDING_LOC = [key for key, value in VOLCS.items() if 'latitude' not in value]

    dbconn = pymysql.connect(user = DB_USER, password = DB_PASS,
                             host = DB_HOST, database = DB_NAME)
    cursor = dbconn.cursor()
    cursor.execute('SELECT volcano_name, latitude, longitude FROM volcano WHERE volcano_name in %s',
                   (VOLCS_NEEDING_LOC, ))

    for volc, lat, lon in cursor:
        VOLCS[volc]['latitude'] = lat
        VOLCS[volc]['longitude'] = lon

    winston_url = config['WINSTON']['url']
    winston_port = config['WINSTON'].getint('port', 16022)
    wclient = WClient(winston_url, winston_port)

    av_avail = wclient.get_availability(network='AV', channel = CHANNEL_MASK)
    ak_avail = wclient.get_availability(network='AK', channel = CHANNEL_MASK)

    # Get metadata about the available stations
    av_meta = get_meta('AV', config)
    ak_meta = get_meta('AK', config)

    av_nets, av_channels = make_net_dict(av_avail, av_meta)
    ak_nets, ak_channels = make_net_dict(ak_avail, ak_meta)

    av_nets['net'] = ['AV'] * len(av_nets)
    ak_nets['net'] = ['AK'] * len(ak_nets)
    all_nets = av_nets.append(ak_nets, ignore_index = True)

    all_channels = dict(av_channels)
    all_channels.update(ak_channels)

    locations = {}
    for volc, info in VOLCS.items():
        lat1 = info['latitude']
        lon1 = info['longitude']
        sort_lon = lon1 if lon1 < 0 else lon1 - 360
        locations[volc] = {
            'sort': sort_lon,
            'stations': [],
        }

        all_nets['dist'] = haversine_np(lon1, lat1, all_nets.longitude, all_nets.latitude)
        max_dist = info.get('radius', 150)
        avail_nets = all_nets.loc[all_nets.dist <= max_dist]
        chosen_nets = avail_nets.sort_values('dist').head(MAX_STATIONS)
        for net in chosen_nets.itertuples():
            sta = net.station
            channels, scales, rates = zip(*all_channels[sta])
            sta_dict = {'STA': sta,
                        'DIST': net.dist, }

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

            locations[volc]['stations'].append(sta_dict)

    with open('specgen/station_config.py', 'w') as conf_file:
        conf_file.write('"""\nThis file is automatically generated by running gen_station_config.py\n')
        conf_file.write('You may modify this file if desired, but be aware any changes will\n')
        conf_file.write('be over-written the next time gen_station_config is run\n"""')
        conf_file.write('\n\n')
        pprinter = pprint.PrettyPrinter(stream = conf_file)
        conf_file.write('locations=')
        pprinter.pprint(dict(locations))


if __name__ == "__main__":
    generate_stations()
