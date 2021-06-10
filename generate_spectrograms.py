from io import StringIO
import csv

from obspy.clients.earthworm import Client as WClient
from obspy import UTCDateTime
from scipy.signal import spectrogram, butter, sosfiltfilt
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
from matplotlib.colors import LogNorm, Normalize
import numpy
import requests

from GenerateColormap import generate_colormap


def main():
    wclient = WClient('pubavo1.wr.usgs.gov', 16022)

    ENDTIME = UTCDateTime(2021, 6, 3, 14, 50)
    STARTTIME = UTCDateTime(2021, 6, 3, 14, 40)

    NET = 'AV'
    STA = 'WAZA'
    CHAN = 'BHZ'

    # Get the waveform data from winston
    stream = wclient.get_waveforms(NET, STA, '--', CHAN,
                                   STARTTIME,
                                   ENDTIME,
                                   cleanup=True
                                   )

    # Get the meta data for this station/channel from IRIS
    meta_url = f'https://service.iris.edu/fdsnws/station/1/query?net={NET}&sta={STA}&cha={CHAN}&starttime={STARTTIME}&endtime={ENDTIME}&level=channel&format=text'
    resp = requests.get(meta_url)

    resp_str = StringIO(resp.text)
    reader = csv.reader(resp_str, delimiter = '|')
    keys = (x.strip() for x in next(reader))
    values = next(reader)
    meta = dict(zip(keys, values))
    resp_str.close()

    # We are only looking at a single trace, so pop that out of the stream
    tr = stream.pop()

    # Get the actual start time from the data, in case it's
    # slightly different from what we requested.
    STARTTIME = UTCDateTime(tr.stats['starttime'])

    # Create an array of timestamps corresponding to the data points
    times = tr.times()
    times = ((times + STARTTIME.timestamp) * 1000).astype('datetime64[ms]')

    # What it says
    tr.detrend()

    # Get the raw data as a numpy array
    data = tr.data

    # Scale the data from counts to real values
    data /= int(float(meta['Scale']))  # meters/second

    # Apply a butterworth bandpass filter to get rid of some noise
    sos = butter(2, [.5, 15], 'bandpass', fs = float(meta['SampleRate']), output = 'sos')
    data = sosfiltfilt(sos, data)

    # Center the data on zero
    data = data - data.mean()

    # Generate the parameters/data for a spectrogram
    spec_info = spectrogram(data, 50, 'hamming', nperseg = 1024,
                            noverlap = 924, nfft = 1024)

    # Convert the times returned from the spectrogram function (0-600 seconds)
    # to real timestamps to line up with the waveform.
    plot_times = spec_info[1]
    plot_times = (plot_times + STARTTIME.timestamp).astype('datetime64[s]')

    # Create a plot figure to hold the waveform and spectrogram graphs
    fig = plt.figure(figsize = (8, 2.0))
    gs = fig.add_gridspec(2, hspace = 0, height_ratios = [1, 5])
    (ax1, ax2) = gs.subplots(sharex = True)

    # Plot the waveform
    ax1.plot(times, data, 'k-', linewidth = .5)
    ax1.set_yticks([])  # No y labels on waveform plot

    # DEBUG testing
    # norm = LogNorm(.002, 20)
    # norm = LogNorm(-10, 20)

    # Generate a linear normilization for the spectrogram.
    # Values here are arbitrary, just what happened to work in testing.
    norm = Normalize(-360, -180)

    cm = generate_colormap()

    spectro = ax2.pcolormesh(
        plot_times, spec_info[0], 20 * numpy.log10(numpy.abs(spec_info[2])),
        norm = norm, cmap = cm, shading = "auto"
    )
    ax2.set_ylim([0, 10])  # 0-10 HZ
    ax2.set_yticks([0, 2, 4, 6, 8])  # Mark even values of frequency
    ax2.set_ylabel(tr.get_id())  # Add the station label
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Format dates as hour:minute
    ax2.set_xlim(times[0], times[-1])  # Expand x axes to the full requested range
    # plt.colorbar(spectro)

    # TODO: save plot image full-size and thumbnail
    plt.show()


if __name__ == "__main__":
    main()
