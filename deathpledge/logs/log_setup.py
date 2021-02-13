"""
My newest headache.

https://stackoverflow.com/questions/45287578/yet-another-python-logging-setup
"""
import os
import yaml
import logging
import logging.config

LOGDIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))
LOGCONFIG_FILE = os.path.join(LOGDIR, '../../config/logging.yaml')


def dp_infologger():
    """Log INFO messages and higher regarding the deathpledge package."""
    logfile = os.path.join(LOGDIR, 'dp_info.log')
    logger = logging.handlers.RotatingFileHandler(
        filename=logfile,
        maxBytes=3*1024**2,  # 3MB
        backupCount=1
    )
    return logger


def dp_debugger():
    """Log DEBUG messages and higher regarding the deathpledge package."""
    logfile = os.path.join(LOGDIR, 'dp_debug.log')
    logger = logging.handlers.RotatingFileHandler(
        filename=logfile,
        maxBytes=3*1024**2,  # 3MB
        backupCount=1
    )
    return logger


def setup_logging(config_path=LOGCONFIG_FILE, default_level=logging.INFO,
                  env_key='LOG_CFG', verbose=None):
    path = config_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        if verbose:
            config['handlers']['console']['level'] = 'DEBUG'
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

