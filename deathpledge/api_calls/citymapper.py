"""Fetch things from the citymapper API."""

import requests
import datetime as dt
from deathpledge.api_calls import keys
from deathpledge import support


class Sleepytime(Exception):
    """Raise when a Citymapper call is made, and you don't want to overload it
    for the next one.
    """
    pass


def get_citymapper_commute_time(startcoords, endcoords):
    """Get commute travel time between two lat/lon tuples from Citymapper API.

    Parameters
    ----------
    startcoords : iterable
        a list or tuple of geographic coordinates (lat/lon) as integers
    endcoords: iterable
        same as startcoords
    Returns
    -------
    str: time in HH:MM:SS
    """
    baseurl = r'https://developer.citymapper.com/api/1/traveltime/'
    url_args = {
        'startcoord': support.str_coords(startcoords),
        'endcoord': support.str_coords(endcoords),
        'time': support.get_commute_datetime('cm'),
        'time_type': 'arrival',
        'key': keys.citymapperKey
    }
    response = requests.get(baseurl, params=url_args)
    print(response.url)
    r_dict = response.json()
    if response.status_code != 200:
        print('Could not retrieve commute time for this address.')
        raise support.BadResponse(r_dict['error_message'])
    try:
        travel_time = r_dict['travel_time_minutes']
    except KeyError as e:
        print(e)
        print('Could not retrieve commute time for this address.')
        raise support.BadResponse('JSON response does not have travel_time_minutes key.')
    return str(dt.timedelta(minutes=travel_time))


if __name__ == '__main__':
    SAMPLE_COORDS = (38.7475034360889, -76.9614514740661)
    SAMPLE_TIME = get_citymapper_commute_time(SAMPLE_COORDS)
    print(SAMPLE_TIME)
