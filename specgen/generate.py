import configparser
import csv
import itertools
import os

from concurrent.futures import ProcessPoolExecutor
from io import StringIO

import numpy
import pandas
import requests

import matplotlib
matplotlib.use('Agg')

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
from matplotlib.colors import Normalize
from obspy.clients.earthworm import Client as WClient
from obspy import UTCDateTime
from scipy.signal import spectrogram

from .colormap import spectro_map
from . import hooks


def init_generation(config):
    global CONFIG

    CONFIG = config


def run_processes(STARTTIME, ENDTIME, executor = None):
    """Get data for all defined stations, generate spectrograms,
    and run any defined hooks for the specified time period."""

    # File path/name is based on ENDTIME
    year = str(ENDTIME.year)
    month = str(ENDTIME.month)
    day = str(ENDTIME.day)
    filename = ENDTIME.strftime('%Y%m%dT%H%M%S') + ".png"
    plot_loc = CONFIG['GLOBAL']['plotimgdir']
    script_loc = os.path.dirname(__file__)
    if not plot_loc.startswith('/'):
        img_base = os.path.realpath(os.path.join(script_loc, plot_loc))
    else:
        img_base = plot_loc

    from .station_config import locations

    procs = []
    for loc, stations in locations.items():
        path = os.path.join(img_base, loc, year, month, day)
        os.makedirs(path, exist_ok = True)
        filepath = os.path.join(path, filename)

        if executor is not None:
            future = executor.submit(generate_spectrogram, filepath, stations, STARTTIME, ENDTIME)
            procs.append(future)
        else:
            # Running single-threaded/process
            generate_spectrogram(filepath, stations, STARTTIME, ENDTIME)

    return procs


def main():
    global CONFIG

    config = configparser.ConfigParser()
    script_loc = os.path.dirname(__file__)
    conf_file = os.path.join(script_loc, 'config.ini')
    config.read(conf_file)
    CONFIG = config

    # TODO: figure out and loop through all time ranges that need to be generated
    # (i.e. current, missed in previous run, etc)

    # Set endtime to the closest 10 minute mark prior to current time
    ENDTIME = UTCDateTime()
    ENDTIME = ENDTIME.replace(minute=ENDTIME.minute - (ENDTIME.minute % 10),
                              second=0,
                              microsecond=0)

    STARTTIME = ENDTIME - (config['GLOBAL'].getint('minutesperimage', 10) * 60)

    gen_times = [(STARTTIME, ENDTIME)]

    procs = []
    with ProcessPoolExecutor(initializer = init_generation,
                             initargs = (config, )) as executor:
        for start, end in gen_times:
            procs += run_processes(start, end, executor)

    for proc in procs:
        print(proc.exception())


def create_df(times, z_data, n_data, e_data):
    if not numpy.asarray([
        numpy.asarray(z_data).size,
        numpy.asarray(n_data).size,
        numpy.asarray(e_data).size
    ]).any():
        raise TypeError("Need at least one of Z, N, or E channel data")

    data = itertools.zip_longest(times, z_data, n_data, e_data,
                                 fillvalue = numpy.nan)
    headers = ['time', 'Z', 'N', 'E']
    df = pandas.DataFrame(data = data, columns = headers)
    return df


def run_hooks(stream, times = None):
    if not hooks.__all__:
        return

    if times is None:
        times = stream[0].times()
        DATA_START = UTCDateTime(stream[0].stats['starttime'])
        times = ((times + DATA_START.timestamp) * 1000).astype('datetime64[ms]')

    try:
        z_data = stream.select(component = 'Z').pop().data
    except:
        z_data = []

    try:
        n_data = stream.select(component = 'N').pop().data
    except Exception as e:
        n_data = []

    try:
        e_data = stream.select(component = 'E').pop().data
    except Exception as e:
        e_data = []

    data_df = create_df(times, z_data, n_data, e_data)
    station = stream.traces[0].get_id().split('.')[1]
    for hook in hooks.__all__:
        try:
            getattr(hooks, hook).run(data_df, station)
        except (AttributeError, TypeError) as e:
            print(f"Unable to run hook '{hook}'", e)
            pass  # No run function, or bad signature


def generate_spectrogram(filename, stations, STARTTIME, ENDTIME):
    # Create a plot figure to hold the waveform and spectrogram graphs
    plot_height = 1.52 * len(stations)
    plot_width = 5.76
    num_plots = 2 * len(stations)
    ratios = [3, 10] * len(stations)
    dpi = 100

    plt.rcParams.update({'font.size': 7})
    fig = plt.figure(dpi = dpi, figsize = (plot_width, plot_height))

    gs = fig.add_gridspec(num_plots, hspace = 0, height_ratios = ratios)
    axes = gs.subplots(sharex = True)

    # Get some config variables
    winston_url = CONFIG['WINSTON']['url']
    winston_port = CONFIG['WINSTON'].getint('port', 16022)

    PAD = 10

    # filter parameters
    low = CONFIG['FILTER'].getfloat('lowcut', 0.5)
    high = CONFIG['FILTER'].getfloat('highcut', 15)
    order = CONFIG['FILTER'].getint('order', 2)

    # spectrogram parameters
    window_type = CONFIG['SPECTROGRAM']['WindowType']
    window_size = CONFIG['SPECTROGRAM'].getint('WindowSize')
    overlap = CONFIG['SPECTROGRAM'].getint('Overlap')
    NFFT = CONFIG['SPECTROGRAM'].getint('NFFT')

    # Spectrogram graph range display
    min_freq = CONFIG['SPECTROGRAM'].getint('MinFreq', 0)
    max_freq = CONFIG['SPECTROGRAM'].getint('MaxFreq', 10)

    wclient = WClient(winston_url, winston_port)

    # Generate a linear normilization for the spectrogram.
    # Values here are arbitrary, just what happened to work in testing.
    norm = Normalize(-360, -180)

    cm = spectro_map()

    for idx, sta_dict in enumerate(stations):
        STA = sta_dict.get('STA')
        CHAN = sta_dict.get('CHAN', 'BHZ')
        NET = sta_dict.get('NET', 'AV')
        station = f"{STA}.{CHAN}"

        # Configure the plot for this station
        ax_idx = 2 * idx
        ax1 = axes[ax_idx]
        ax2 = axes[ax_idx + 1]

        ax1.set_yticks([])  # No y labels on waveform plot

        ticklen = 8

        ax2.set_ylim([min_freq, max_freq])
        ax2.set_yticks(numpy.arange(min_freq, max_freq, 2))  # Mark even values of frequency
        ax2.set_ylabel(station)  # Add the station label
        ax2.xaxis.set_tick_params(direction='inout', bottom = True,
                                  top = True, length = ticklen)
        ax2.yaxis.set_tick_params(direction = "in", right = True)

        direction = "inout"
        if idx == 0:
            direction = "in"
            ticklen /= 2

        ax1.xaxis.set_tick_params(direction = direction, bottom = True,
                                  top = True, length = ticklen)
        ax1.yaxis.set_tick_params(left = False)

        # Get the data for this station from the winston server
        CHAN_WILD = CHAN[:-1] + '*'
        stream = wclient.get_waveforms(
            NET, STA, '--', CHAN_WILD,
            STARTTIME - PAD,
            ENDTIME + PAD,
            cleanup=True
        )

        if stream.count() == 0:
            # TODO: Make note of no data for this station/time range, and check again later
            continue  # No data for this station, so just leave an empty plot

        # What it says
        stream.detrend()

        # Apply a butterworth bandpass filter to get rid of some noise
        stream.filter('bandpass', freqmin = low, freqmax = high,
                      corners = order, zerophase = True)

        # Merge any gaped traces
        stream = stream.merge(method = 1, fill_value = numpy.nan,
                              interpolation_samples = -1)

        # And pad out any short traces
        stream.trim(STARTTIME - PAD, ENDTIME + PAD, pad = True, fill_value = numpy.nan)

        if stream[0].count() < window_size:
            # Not enough data to work with
            continue

        # Get the actual start time from the data, in case it's
        # slightly different from what we requested.
        DATA_START = UTCDateTime(stream[0].stats['starttime'])

        # Create an array of timestamps corresponding to the data points
        waveform_times = stream[0].times()
        waveform_times = ((waveform_times + DATA_START.timestamp) * 1000).astype('datetime64[ms]')

        for trace in stream:
            scale = sta_dict['SCALE']
            trace.data /= scale
            trace.data = trace.data - trace.data.mean()

        # Get the raw z data as a numpy array
        z_data = stream.select(component = 'Z').pop().data

        # Run any files in the hooks directory with this data
        run_hooks(stream, waveform_times)

        # Generate the parameters/data for a spectrogram
        sample_rate = sta_dict['SAMPLE_RATE']
        spec_info = spectrogram(z_data, sample_rate, window_type, nperseg = window_size,
                                noverlap = overlap, nfft = NFFT)

        # Convert the times returned from the spectrogram function (0-600 seconds)
        # to real timestamps to line up with the waveform.
        spectrograph_times = spec_info[1]
        spectrograph_times = (spectrograph_times + DATA_START.timestamp).astype('datetime64[s]')

        # Plot the waveform
        ax1.plot(waveform_times, z_data, 'k-', linewidth = .5)

        # And the spectrogram
        ax2.pcolormesh(
            spectrograph_times, spec_info[0], 20 * numpy.log10(numpy.abs(spec_info[2])),
            norm = norm, cmap = cm, shading = "auto"
        )

        ax2.set_xlim(STARTTIME, ENDTIME)  # Expand x axes to the full requested range

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Format dates as hour:minute
    # TODO: save plot image full-size and thumbnail
    side_padding = 25 / (plot_width * dpi)
    bottom_padding = 25 / (plot_height * dpi)
    fig.tight_layout(pad = 0, rect = (side_padding, bottom_padding,
                                      1 - side_padding, 1))

    fig.savefig(filename)
    print(filename)
    gen_thumbnail(filename, fig)


def gen_thumbnail(filename, fig):
    small_path = list(os.path.split(filename))
    small_path[-1] = "small_" + small_path[-1]
    filename = os.path.join(*small_path)
    axes = fig.axes
    for ax in axes:
        ax.xaxis.set_tick_params(top = False, bottom = False)
        ax.yaxis.set_tick_params(left = False, right = False)
        ax.set_ylabel("")
        ax.axis("off")

    thumb_height = .396 * (len(axes) / 2)
    thumb_width = 1.5
    fig.set_size_inches(thumb_width, thumb_height)
    fig.tight_layout(pad = 0)

    fig.savefig(filename, transparent = False, pad_inches=0)


if __name__ == "__main__":
    import time
    t1 = time.time()
    main()
    print("Completed run after:", time.time() - t1)
