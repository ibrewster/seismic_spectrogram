import configparser
import os


def load_config():
    config = configparser.ConfigParser()
    script_loc = os.path.dirname(__file__)
    conf_file = os.path.join(script_loc, 'config.ini')
    config.read(conf_file)
    return config


config = load_config()

from .station_config import locations, stations
