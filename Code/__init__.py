from os import path

PROJ_PATH = path.normpath(path.join(path.dirname(path.realpath(__file__)), '..'))
print(PROJ_PATH)
