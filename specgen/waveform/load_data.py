import numpy

from obspy.clients.earthworm import Client as WClient
from obspy import UTCDateTime

from . import config as CONFIG, AvailabilityError, stations


def load(network = None, station = None, location = None,
         channel = None, starttime = None, endtime = None):
    """
    Load and clean waveform data from a winston server.
    Takes a number of optional filtering parameters and returns
    a stream object as well as a list of times for the points in
    the stream object, or (None, None) if no data is available
    for the specified parameters

    PARAMETERS
    ----------
    network: str or None
    station: str or None
    location: str or None
    channel: str or None
    starttime: utcdatetime or None
    endtime: utcdatetime or None

    RETURNS
    -------
    stream: ObsPy stream or None
    waveform_times: list or None
    """
    kwargs = locals().copy()

    # Get some config variables
    winston_url = CONFIG['WINSTON']['url']
    winston_port = CONFIG['WINSTON'].getint('port', 16022)

    # filter parameters
    low = CONFIG['FILTER'].getfloat('lowcut', 0.5)
    high = CONFIG['FILTER'].getfloat('highcut', 15)
    order = CONFIG['FILTER'].getint('order', 2)

    window_size = CONFIG['SPECTROGRAM'].getint('WindowSize', fallback = None)
    PAD = CONFIG['SPECTROGRAM'].getint('padding', fallback = 10)

    wclient = WClient(winston_url, winston_port)

    args = {key: value for key, value in
            kwargs.items()
            if value is not None and
            key not in ('starttime', 'endtime')}

    avail = wclient.get_availability(**args)

    try:
        avail_from = avail[0][4]
        avail_to = avail[0][5]
        if avail_to < starttime or avail_from > endtime:
            raise AvailabilityError("No data for this timeframe")

        # TODO: flag limited data availability
    except (IndexError, AvailabilityError):
        with open('/tmp/plots/AAA.txt', 'a') as errFile:
            errFile.write(f"Availability error for {station}\n")
        # No availability for this station/timerange
        return (None, None)

    args = {key: value for key, value in kwargs.items() if value is not None}
    if 'starttime' in args:
        args['starttime'] -= PAD
    if 'endtime' in args:
        args['endtime'] += PAD

    stream = wclient.get_waveforms(
        cleanup=True,
        **args
    )

    if stream.count() == 0:
        with open('/tmp/plots/AAA.txt', 'a') as errFile:
            errFile.write(stream[0].id)
            errFile.write(' (counts): ')
            errFile.write(str(stream.count()) + "/n")
        return (None, None)  # No data for this station, so just leave an empty plot

    # Merge any gaped traces
    # Everything needs to be the same dtype
    for tr in stream:
        tr.data = tr.data.astype(int)

    stream = stream.merge(method = 1, fill_value = 'latest',
                          interpolation_samples = -1)

    if window_size is not None and stream[0].count() < window_size:
        # Not enough data to work with
        with open('/tmp/plots/AAA.txt', 'a') as errFile:
            errFile.write(stream[0].id)
            errFile.write(': ')
            errFile.write(str(stream[0].count()))
            errFile.write(' ')
            errFile.write(str(window_size) + '\n')
        return (None, None)

    # What it says
    stream.detrend()

    # Apply a butterworth bandpass filter to get rid of some noise
    stream.filter('bandpass', freqmin = low, freqmax = high,
                  corners = order, zerophase = True)

    # And pad out any short traces
    stream.trim(starttime - PAD, endtime + PAD, pad = True, fill_value = numpy.nan)

    # Get the actual start time from the data, in case it's
    # slightly different from what we requested.
    DATA_START = UTCDateTime(stream[0].stats['starttime'])

    # Create an array of timestamps corresponding to the data points
    waveform_times = stream[0].times()
    waveform_times = ((waveform_times + DATA_START.timestamp) * 1000).astype('datetime64[ms]')
    scale = stations[station]['SCALE']

    for trace in stream:
        trace.data /= scale
        trace.data = trace.data - trace.data.mean()

    return (stream, waveform_times)
