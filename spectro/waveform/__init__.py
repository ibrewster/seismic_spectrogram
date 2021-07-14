class AvailabilityError(Exception):
    pass


def _init():
    import sys
    import os
    file_path = os.path.dirname(__file__)
    parent_path = os.path.realpath(os.path.join(file_path, '..'))
    sys.path.append(parent_path)


_init()

from config import config, stations

from .load_data import load
