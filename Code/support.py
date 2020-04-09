"""Generic functions to support other modules."""

import requests
import random
from math import radians, cos, sin, asin, sqrt
import datetime
from datetime import datetime as dt
import time
from fake_useragent import UserAgent
from django.utils.text import slugify
from hashlib import sha1


class BadResponse(Exception):
    pass


def timing(f):

    def timed(*args, **kw):

        start = dt.now()
        print(f'Start: {start}')
        result = f(*args, **kw)
        finish = dt.now()
        print(f'Finish: {finish} ({finish-start})')
        return result

    return timed


def initialize_listing_dict():
    """Create an empty listing dict to provide the backbone to the house file.

    The structure needed is the outer dicts (categories) comprised
    of empty dictionaries to be filled with field: value pairs.

    Here you can specify the precise order of the dict keys, because
    as of Python 3.7, insertion order in dicts is preserved.

    Returns: dict
    """
    cat_list = [
        '_metadata',
        '_info',
        'basic info',
        'property / unit information',
        'building information',
        'exterior information',
        'association / location / schools',
        'expenses / taxes',
        'utilities',
        'listing history',
        'local travel',
        'comments',
        'quickstats'
    ]
    dic = {}
    for category in cat_list:
        dic.setdefault(category, {})
    return dic


def str_coords(coords):
    str_list = [str(x) for x in coords]
    return ','.join(str_list)


# TODO: is this getting used anywhere??
def check_status_of_website(url):
    """Make sure get() returns a 200"""
    ua = UserAgent()
    header = {'User-Agent': str(ua.firefox)}
    result = requests.get(url, headers=header)
    time.sleep(random.random()*10)
    return result.status_code


def get_commute_datetime(mode, dayofweek=1, hrmin='06:30'):
    """Get my work commute time for the next day specified.

    By default, work time is 06:30 and day is Tuesday.
    Adapted from SO 6558535

    Args:
        mode (str): Determines how to format the resulting string.
            Either 'bing', or 'cm' for citymapper.
        dayofweek (int, optional): Index of weekday. Defaults to 1 (Tuesday).
            0=Mon, 1=Tue, 2=Wed, 3=Thur, 4=Fri, 5=Sat, 6=Sun
        hrmin (str, optional): 24-hour specifying departure or arrival time. Defaults to 6:30 AM.
            It's the departure time if driving, arrival time if transit.

    Returns:
        str: Formatted as datetime for chosen *mode*.

    """
    now = dt.now()
    days_ahead = dayofweek - now.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    wday = now + datetime.timedelta(days_ahead)
    wtime = dt.strptime(hrmin, '%H:%M').time()
    work_datetime = dt(wday.year, wday.month, wday.day, wtime.hour, wtime.minute)

    # Format for mode
    if mode == 'cm':
        return '{}-0400'.format(work_datetime.isoformat())
    elif mode == 'bing':
        # dateTime=03/01/2011 05:42:00
        return work_datetime.strftime('%m/%d/%Y %H:%M:%S')


def str_time_to_min(s):
    """Converts a HH:MM:SS string to decimal minutes."""
    try:
        dur = dt.strptime(s.split()[0], '%H:%M:%S')
    except (TypeError, ValueError):
        return None
    delta = datetime.timedelta(hours=dur.hour, minutes=dur.minute, seconds=dur.second)
    return delta.total_seconds()/60


def haversine(coords1, coords2):
    """ Get distance between two lat/lon pairs using the Haversine formula."""
    lat1, lon1 = coords1
    lat2, lon2 = coords2
    R = 3959.87433  # this is in miles. For kilometers use 6372.8 km

    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
    c = 2*asin(sqrt(a))
    return R * c


def create_filename_from_addr(addr):
    """Generate a JSON filename from house address."""
    filename = clean_address(addr).replace(' ', '_')
    return '{}.json'.format(filename)


def clean_address(addr):
    """Standardize house address for filenames and doc ID."""
    return slugify(addr).replace('-', ' ').upper()


def create_house_id(addr):
    """Get SHA-1 hash from address."""
    clean_addr = clean_address(addr)
    return sha1(clean_addr.encode()).hexdigest()


if __name__ == '__main__':
    pass
