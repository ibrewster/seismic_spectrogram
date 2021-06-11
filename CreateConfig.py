import configparser

config = configparser.ConfigParser()
config['GLOBAL'] = {'MinutesPerImage': 10}

config['WINSTON'] = {'url': 'pubavo1.wr.usgs.gov',
                     'port': 16022, }

config['IRIS'] = {'url': 'https://service.iris.edu/fdsnws/station/1/query?', }

config['FILTER'] = {
    'LowCut': .5,
    'HighCut': 15,
    'Order': 2,
}

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
