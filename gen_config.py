import configparser

config = configparser.ConfigParser()
config['GLOBAL'] = {
    'MinutesPerImage': 10
}

config['WINSTON'] = {'url': 'pubavo1.wr.usgs.gov',
                     'port': 16022, }

config['IRIS'] = {'url': 'https://service.iris.edu/fdsnws/station/1/query?', }

# Data filters to apply to the raw data
config['FILTER'] = {
    'LowCut': .5,
    'HighCut': 15,
    'Order': 2,
}


# Parameters for generating the seismic spectrogram function
config['SPECTROGRAM'] = {
    'WindowType': 'hamming',
    'WindowSize': 1024,
    'Overlap': 924,
    'NFFT': 1024,
    'MaxFreq': 10,
    'MinFreq': 0,
}

with open('config.ini', 'w') as conffile:
    config.write(conffile)
