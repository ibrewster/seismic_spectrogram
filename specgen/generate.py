import bz2
import os
import pickle
import sqlite3


from concurrent.futures import ProcessPoolExecutor

from matplotlib import pyplot as plt
from obspy import UTCDateTime


from . import graphing

from .waveform import load
from .config import config, stations


class AvailabilityError(Exception):
    pass


def main():
    #     tempdir = os.path.join(tempfile.gettempdir(), "specgenTemp")
    #     if os.path.exists(tempdir):
    #         shutil.rmtree(tempdir)
    #
    #     print("Creating tempdir:", tempdir)
    #     os.makedirs(tempdir, exist_ok = True)

    # TODO: figure out and loop through all time ranges that need to be generated
    # (i.e. current, missed in previous run, etc)

    # Set endtime to the closest 10 minute mark prior to current time
    ENDTIME = UTCDateTime()
    ENDTIME = ENDTIME.replace(minute=ENDTIME.minute - (ENDTIME.minute % 10),
                              second=0,
                              microsecond=0)

    STARTTIME = ENDTIME - (config['GLOBAL'].getint('minutesperimage', 10) * 60)

    gen_times = [(STARTTIME, ENDTIME, None)]

    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok = True)
    cache_db = os.path.join(cache_dir, 'cache.db')
    with sqlite3.connect(cache_db) as conn:
        cur = conn.cursor()
        # Make sure the "missed" table exists
        cur.execute("CREATE TABLE IF NOT EXISTS missed (station TEXT, dtfrom TEXT, dtto TEXT, UNIQUE (station, dtfrom, dtto))")
        cur.execute("SELECT station,dtfrom,dtto FROM missed ORDER BY dtto DESC")  # May be empty

        for station, dtfrom, dtto in cur:
            loc = {station: stations[station]}
            dtfrom = UTCDateTime(dtfrom)
            dtto = UTCDateTime(dtto)
            if (UTCDateTime() - dtfrom) / 60 / 60 > 2:
                continue  # Don't try to go back more than two hours
            gen_times.append((dtfrom, dtto, loc))

        cur.execute("DELETE FROM missed")  # Potential race condition between SELECT and DELETE?

    plot_loc = config['GLOBAL']['plotimgdir']
    script_loc = os.path.dirname(__file__)

    if not plot_loc.startswith('/'):
        img_base = os.path.realpath(os.path.join(script_loc, plot_loc))
    else:
        img_base = plot_loc

    procs = []
    with ProcessPoolExecutor() as executor:
        for start, end, locs in gen_times:
            # File path/name is based on ENDTIME
            year = str(end.year)
            month = str(end.month)
            day = str(end.day)
            filename = end.strftime('%Y%m%dT%H%M%S') + ".png"

            if locs is None:
                locs = stations
            for loc, loc_info in locs.items():
                path = os.path.join(img_base, loc, year, month, day)
                os.makedirs(path, exist_ok = True)
                filepath = os.path.join(path, filename)
                # generate_spectrogram(filepath, loc, loc_info, start, end)
                future = executor.submit(generate_spectrogram, filepath,
                                         loc, loc_info, start, end)
                procs.append((loc, start, end, future))

    INSERT_SQL = """
    INSERT INTO missed
    (station, dtfrom, dtto)
    VALUES
    (?,?,?)
    """
    for station, dtstart, dtend, proc in procs:
        try:
            missed_flag = proc.result()
        except Exception as e:
            print(e)
            missed_flag = True

        if missed_flag:
            with sqlite3.connect(cache_db) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(INSERT_SQL,
                                (station,
                                 dtstart.isoformat(),
                                 dtend.isoformat()))
                except sqlite3.IntegrityError:
                    # Already marked this volc/timerange as missing
                    continue

                conn.commit()


# def create_df(times, z_data, n_data, e_data):
#     if not numpy.asarray([
#         numpy.asarray(z_data).size,
#         numpy.asarray(n_data).size,
#         numpy.asarray(e_data).size
#     ]).any():
#         raise TypeError("Need at least one of Z, N, or E channel data")
#
#     data = itertools.zip_longest(times, z_data, n_data, e_data,
#                                  fillvalue = numpy.nan)
#     headers = ['time', 'Z', 'N', 'E']
#     df = pandas.DataFrame(data = data, columns = headers)
#     return df


# def run_hooks(stream, times = None):
#     if not hooks.__all__:
#         return
#
#     if times is None:
#         times = stream[0].times()
#         DATA_START = UTCDateTime(stream[0].stats['starttime'])
#         times = ((times + DATA_START.timestamp) * 1000).astype('datetime64[ms]')
#
#     try:
#         z_data = stream.select(component = 'Z').pop().data
#     except:
#         z_data = []
#
#     try:
#         n_data = stream.select(component = 'N').pop().data
#     except Exception as e:
#         n_data = []
#
#     try:
#         e_data = stream.select(component = 'E').pop().data
#     except Exception as e:
#         e_data = []
#
#     data_df = create_df(times, z_data, n_data, e_data)
#     station = stream.traces[0].get_id().split('.')[1]
#     for hook in hooks.__all__:
#         try:
#             getattr(hooks, hook).run(data_df, station)
#         except AttributeError:
#             pass  # We already warned this hook would be unavailable
#         except TypeError as e:
#             warnings.warn(f"Unable to run hook '{hook}' {e}",
#                           hooks.HookWarning,
#                           stacklevel=2)
#             pass  # No run function, or bad signature


def generate_spectrogram(filename, STA, sta_dict, STARTTIME, ENDTIME):
    CHAN = sta_dict.get('CHAN', 'BHZ')
    NET = sta_dict.get('NET', 'AV')

    # Get the data for this station from the winston server
    stream, waveform_times = load(NET, STA, '--', CHAN,
                                  STARTTIME, ENDTIME)

    if stream is None or waveform_times is None:
        return True  # missed this station/time

    # Get the raw z data as a numpy array
    z_data = stream.select(component = 'Z').pop()

    data_file = filename[:-3] + "pbz2"
    with bz2.BZ2File(data_file, 'w') as figure_file:
        pickle.dump(waveform_times, figure_file)
        pickle.dump(z_data, figure_file)

    print(filename)
    # Save the thumbnail for this spectrogram
    fig = graphing.gen_spectrograph(waveform_times, z_data)
    graphing.gen_thumbnail(filename, fig)
    plt.close(fig)

    return False  # Did NOT miss this station


if __name__ == "__main__":
    import time
    t1 = time.time()
    main()
    print("Completed run after:", time.time() - t1)
