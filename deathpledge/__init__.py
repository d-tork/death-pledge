from os import path, makedirs
from sys import platform

PROJ_PATH = path.normpath(path.join(path.dirname(path.realpath(__file__)), '..'))
LISTINGS_DIR = path.join(PROJ_PATH, 'data', 'Processed', 'saved_listings')
LISTINGS_GLOB = path.join(PROJ_PATH, 'data', 'Processed', 'saved_listings', '*.json')
SCORECARD_PATH = path.join(PROJ_PATH, 'data', 'scorecard.json')
DATABASE_NAME = 'deathpledge_clean_flat'
RAW_DATABASE_NAME = 'deathpledge_raw_flat'
TIMEFORMAT = '%Y-%m-%dT%H:%M:%S'

if platform == 'linux':
    GECKODRIVER_PATH = path.join(PROJ_PATH, 'deathpledge', 'Drivers', 'geckodriver_linux')
else:
    GECKODRIVER_PATH = path.join(PROJ_PATH, 'deathpledge', 'Drivers', 'geckodriver')

makedirs(LISTINGS_DIR, exist_ok=True)

