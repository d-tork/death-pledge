"""Fetch things from the citymapper API."""

import requests
import datetime as dt
from time import sleep
from Code.api_calls import coordinates
from Code.api_calls import keys

BASEURL = r'https://developer.citymapper.com/api/1/traveltime/'


def str_coords(coords):
    str_list = [str(x) for x in coords]
    return ','.join(str_list)


def get_commute_datetime(dayofweek=2):
    """Get my work commute time for the next day specified.

    By default, work time is 07:00 and day is Tuesday.
    """
    import datetime as dt
    now = dt.datetime.now()
    wday = now + dt.timedelta(days=(dayofweek + 7 - now.weekday()))  # SO 6558535
    wtime = dt.time(7, 0)
    work_datetime = dt.datetime(wday.year, wday.month, wday.day, wtime.hour, wtime.minute)
    return work_datetime.isoformat()


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
        'startcoord': str_coords(startcoords),
        'endcoord': str_coords(keys.work_coords),
        'time': get_commute_datetime(),
        'time_type': 'arrival',
        'key': keys.citymapperKey
    }
    response = requests.get(BASEURL, params=url_args)
    print(response.url)
    if response.status_code == 400:
        print('Could not retrieve commute time for this address.')
        return None
    r_dict = response.json()
    try:
        travel_time = str(dt.timedelta(minutes=r_dict['travel_time_minutes']))
    except KeyError as e:
        print(e)
        print('Could not retrieve commute time for this address.')
        return None
    print(travel_time)
    sleep(10)
    return travel_time


if __name__ == '__main__':
    SAMPLE_COORDS = (38.7475034360889, -76.9614514740661)
    SAMPLE_TIME = get_commute_time(SAMPLE_COORDS)
    print(SAMPLE_TIME)
