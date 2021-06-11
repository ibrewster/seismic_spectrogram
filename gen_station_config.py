import configparser
import pprint

from collections import defaultdict
from obspy.clients.earthworm import Client as WClient

DEFAULT_CHANNEL = 'BHZ'
ALT_CHANNELS = ['SHZ']
station_config = {
    'Spurr': {
        'PREFIX': 'SP',
        'OTHER': [
            'N20K'
        ],
    },
    'Wrangel': {
        'PREFIX': 'WA',
        'OTHER': [
            'M26K',
            'N25K'
        ],
    },
    'Redoubt': {
        'PREFIX': 'RD',
        'OTHER': [
            'RED',
            'NCT'
        ],
        'EXCLUDE': [
            'RDT'
        ],
    },
    'Iliamna': {
        'PREFIX': 'IL',
        'OTHER': [
            'IVE',
            'P19K'
        ],
        'EXCLUDE': [
            'ILCB',
            'ILNE'
        ],
    },
}

locations = defaultdict(list)

config = configparser.ConfigParser()
config.read("config.ini")

winston_url = config['WINSTON']['url']
winston_port = config['WINSTON'].getint('port', 16022)
wclient = WClient(winston_url, winston_port)

for loc, info in station_config.items():
    NET = 'AV'  # may be AK
    STA = info['PREFIX'] + "*"
    OTHER = info.get("OTHER", [])
    EXCLUDE = info.get('EXCLUDE', [])

    avail_channels = defaultdict(list)
    ak_stations = []

    avail = wclient.get_availability(network=NET, station = STA)
    for oth in OTHER:
        oth_avail = wclient.get_availability(network=NET, station = oth)
        if not oth_avail:  # Try the AK network
            oth_avail = wclient.get_availability(network='AK', station = oth)

        avail += oth_avail

    for entry in avail:
        station = entry[1]
        if station in EXCLUDE:
            continue

        channel = entry[3]
        network = entry[0]
        avail_channels[station].append(channel)
        if network != 'AV':
            ak_stations.append(station)

    for station, channels in avail_channels.items():
        sta_dict = {'STA': station}
        if not 'BHZ' in channels:
            for alt_chan in ALT_CHANNELS:
                if alt_chan in channels:
                    sta_dict['CHAN'] = alt_chan
                    break
            else:
                continue  # No good channels found for this station, move on
        if station in ak_stations:
            sta_dict['NET'] = 'AK'

        locations[loc].append(sta_dict)

with open('station_config.py', 'w') as conf_file:
    pprinter = pprint.PrettyPrinter(stream = conf_file)
    conf_file.write('locations=')
    pprinter.pprint(dict(locations))
