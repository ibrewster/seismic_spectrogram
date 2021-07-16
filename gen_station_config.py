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

####################################################
#  User editable options for the station configuration
#
# Change values below to set the parameters used when
# generating the station config file
####################################################
# Search for all channels matching the below mask
CHANNEL_MASK = '[SB]HZ'

# The default channel to use if more than one are found
DEFAULT_CHANNEL = 'BHZ'

# Which networks to search for stations
NETWORKS = ['AV', 'AK']

# Maximum number of stations to show per volcano plot
MAX_STATIONS = 10

# Only include stations that have received data within this time period (seconds)
MAX_AGE = 1 * 24 * 60 * 60  # 1 days

# Maximum distance from volcano to search for stations.
# Can be over-ridden on a per-volcano basis in the VOLCS list, below
DEFAULT_RADIUS = 150

# Dictionary of volcanos to look at, and the radius
# around them to search for active stations.
# If latitude and longitude is specified,
# it will be used, otherwise we will try to pull latitude/longitude information
# from the database specified in the config. An empty dict means use defaults
# and pull latitude/longitude from DB.
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
    config.read("specgen/config/config.ini")

    # Get volcano locations
    VOLCS_NEEDING_LOC = [key for key, value in VOLCS.items() if 'latitude' not in value]

    # Don't try to do the query if there are no volcs needing lat/lon information
    if VOLCS_NEEDING_LOC:
        import pymysql  # Import here just in case we don't actually need it

        DB_HOST = config['MySQL']['db_host']
        DB_USER = config['MySQL']['db_user']
        DB_PASS = config['MySQL']['db_password']
        DB_NAME = config['MySQL']['db_name']

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

    all_channels = {}
    all_nets = None
    for network in NETWORKS:
        # Get availability information for the network
        avail = wclient.get_availability(network=network, channel = CHANNEL_MASK)
        # get metadata for the network
        meta = get_meta(network, config)
        nets, channels = make_net_dict(avail, meta)
        nets['net'] = [network] * len(nets)
        if all_nets is None:
            all_nets = nets
        else:
            all_nets = all_nets.append(nets)

        all_channels.update(channels)

    locations = {}
    stations = {}
    for volc, info in VOLCS.items():
        lat1 = info['latitude']
        lon1 = info['longitude']
        sort_lon = lon1 if lon1 < 0 else lon1 - 360
        locations[volc] = {
            'sort': sort_lon,
            'stations': [],
        }

        all_nets['dist'] = haversine_np(lon1, lat1, all_nets.longitude, all_nets.latitude)
        max_dist = info.get('radius', DEFAULT_RADIUS)
        avail_nets = all_nets.loc[all_nets.dist <= max_dist]
        chosen_nets = avail_nets.sort_values('dist').head(MAX_STATIONS)
        for net in chosen_nets.itertuples():
            sta = net.station
            channels, scales, rates = zip(*all_channels[sta])
            locations[volc]['stations'].append((sta, net.dist))
            if sta not in stations:
                sta_dict = {}

                if DEFAULT_CHANNEL not in channels:
                    sta_dict['CHAN'] = channels[0]
                    sta_dict['SCALE'] = scales[0]
                    sta_dict['SAMPLE_RATE'] = rates[0]
                else:
                    chan_idx = channels.index(DEFAULT_CHANNEL)
                    sta_dict['CHAN'] = DEFAULT_CHANNEL
                    sta_dict['SCALE'] = scales[chan_idx]
                    sta_dict['SAMPLE_RATE'] = rates[chan_idx]

                sta_dict['NET'] = net.net

                stations[sta] = sta_dict

    with open('specgen/config/station_config.py', 'w') as conf_file:
        conf_file.write('"""\nThis file is automatically generated by running gen_station_config.py\n')
        conf_file.write('You may modify this file if desired, but be aware any changes WILL\n')
        conf_file.write('be over-written the next time gen_station_config is run\n"""')
        conf_file.write('\n\n')
        pprinter = pprint.PrettyPrinter(stream = conf_file)
        conf_file.write('locations=')
        pprinter.pprint(locations)
        conf_file.write('\n\n')
        conf_file.write('stations=')
        pprinter.pprint(stations)


if __name__ == "__main__":
    generate_stations()
