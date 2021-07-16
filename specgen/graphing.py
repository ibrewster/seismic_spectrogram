import os
import numpy

import matplotlib
matplotlib.use('Agg')

import matplotlib.dates as mdates
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
import pandas
from scipy.signal import spectrogram

from .config import config
from .colormap import spectro_map


def gen_spectrograph(times, data):
    data.plot(outfile = f"/tmp/plots/{data.id}test-2.png")
    # Create a plot figure to hold the waveform and spectrogram graphs
    plot_height = 1.52
    plot_width = 5.76
    num_plots = 2
    ratios = [3, 10]
    dpi = 100

    plt.rcParams.update({'font.size': 7})

    fig = plt.figure(dpi = dpi, figsize = (plot_width, plot_height))

    gs = fig.add_gridspec(num_plots, hspace = 0, height_ratios = ratios)
    axes = gs.subplots(sharex = True)

    # Configure the plot for this station
    ax1 = axes[0]
    ax2 = axes[1]
    gen_station_subplots(times, data, ax1, ax2)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Format dates as hour:minute

    side_padding = 25 / (plot_width * dpi)
    bottom_padding = 25 / (plot_height * dpi)
    fig.tight_layout(pad = 0, rect = (side_padding, bottom_padding,
                                      1 - side_padding, 1))

    return fig


def gen_station_subplots(times, data, ax1, ax2):
    # spectrogram parameters
    window_type = config['SPECTROGRAM']['WindowType']
    window_size = config['SPECTROGRAM'].getint('WindowSize')
    overlap = config['SPECTROGRAM'].getint('Overlap')
    NFFT = config['SPECTROGRAM'].getint('NFFT')

    # Generate the parameters/data for a spectrogram
    sample_rate = data.stats['sampling_rate']
    z_data = data.data

    spec_info = spectrogram(z_data, sample_rate, window_type, nperseg = window_size,
                            noverlap = overlap, nfft = NFFT)

    # Convert the times returned from the spectrogram function (0-600 seconds)
    # to real timestamps to line up with the waveform.
    spectrograph_times = spec_info[1]
    DATA_START = data.stats['starttime']
    spectrograph_times = (spectrograph_times + DATA_START.timestamp).astype('datetime64[s]')

    # Generate a linear normilization for the spectrogram.
    # Values here are arbitrary, just what happened to work in testing.
    norm = Normalize(-360, -180)

    cm = spectro_map()

    ticklen = 4

    station = data.stats['station']
    channel = data.stats['channel']
    station_label = f"{station}.{channel}"

    configure_spectrograph_y(station_label, ax1, ax2)

    direction = "in"

    ax1.xaxis.set_tick_params(direction = direction, bottom = True,
                              top = True, length = ticklen)

    # Plot the waveform
    ax1.plot(times, z_data, 'k-', linewidth = .5)

    # And the spectrogram
    ax2.pcolormesh(
        spectrograph_times, spec_info[0], 20 * numpy.log10(numpy.abs(spec_info[2])),
        norm = norm, cmap = cm, shading = "auto"
    )

    # Set range to exact 10 minute mark
    range_start = times[0]
    if (pandas.Timestamp(range_start).second > 30):
        range_start = (range_start + numpy.timedelta64(1, 'm'))
    range_start = range_start.astype('datetime64[m]')

    range_end = times[-1]
    range_end = range_end.astype('datetime64[m]')

    ax2.set_xlim(range_start, range_end)  # Expand x axes to the full requested range


def configure_spectrograph_y(station_label, ax1, ax2):
    # Spectrogram graph range display
    min_freq = config['SPECTROGRAM'].getint('MinFreq', 0)
    max_freq = config['SPECTROGRAM'].getint('MaxFreq', 10)

    ticklen = 4

    ax1.set_yticks([])  # No y labels on waveform plot
    ax1.yaxis.set_tick_params(left = False)

    ax2.set_ylim([min_freq, max_freq])
    ax2.set_yticks(numpy.arange(min_freq, max_freq, 2))  # Mark even values of frequency
    ax2.set_ylabel(station_label)  # Add the station label
    ax2.xaxis.set_tick_params(direction='inout', bottom = True,
                              top = True, length = ticklen)
    ax2.yaxis.set_tick_params(direction = "in", right = True)


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
