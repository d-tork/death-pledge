"""Fetch things from the citymapper API."""

import requests
import datetime as dt
import keys
import coordinates
import support

BASEURL = r'https://developer.citymapper.com/api/1/traveltime/'


def get_commute_time(startcoords):
    """Get commute travel time between a given lat/lon and workplace.

    Parameters
    ----------
    startcoords : iterable
        a list or tuple of geographic coordinates (lat/lon) as integers

    Returns
    -------
    hour(s) and minutes as string
    """
    url_args = {
        'startcoord': support.str_coords(coordinates.coords),
        'endcoord': support.str_coords(keys.work_coords),
        'time': keys.get_commute_datetime(),
        'time_type': 'arrival',
        'key': keys.citymapperKey
    }
    response = requests.get(BASEURL, params=url_args)
    print(response.url)
    r_dict = response.json()
    travel_time = str(dt.timedelta(minutes=r_dict['travel_time_minutes']))
    print(travel_time)
    return travel_time

get_commute_time(support.str_coords(coordinates.coords))
