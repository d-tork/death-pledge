from os import path, makedirs
from sys import platform
import yaml

PROJ_PATH = path.normpath(path.join(path.dirname(path.realpath(__file__)), '..'))
CONFIG_PATH = path.join(PROJ_PATH, 'config')
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


def read_keys_file():
    keys_path = path.join(CONFIG_PATH, 'keys.yaml')
    with open(keys_path, 'r') as f:
        return yaml.safe_load(f)


keys = read_keys_file()
