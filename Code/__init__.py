from os import path

PROJ_PATH = path.normpath(path.join(path.dirname(path.realpath(__file__)), '..'))
GECKODRIVER_PATH = path.join(PROJ_PATH, 'Code', 'Drivers', 'geckodriver')
