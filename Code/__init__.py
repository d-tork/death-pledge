from os import path, makedirs

PROJ_PATH = path.normpath(path.join(path.dirname(path.realpath(__file__)), '..'))
GECKODRIVER_PATH = path.join(PROJ_PATH, 'Code', 'Drivers', 'geckodriver')
LISTINGS_DIR = path.join(PROJ_PATH, 'Data', 'Processed', 'saved_listings')
LISTINGS_GLOB = path.join(PROJ_PATH, 'Data', 'Processed', 'saved_listings', '*.json')
SCORECARD_PATH = path.join(PROJ_PATH, 'Data', 'scorecard.json')

makedirs(LISTINGS_DIR, exist_ok=True)

