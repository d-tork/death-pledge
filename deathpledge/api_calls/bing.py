"""
Update properties retrieved with Bing Maps.
"""

import requests
import datetime as dt
from deathpledge import keys
from deathpledge import support

bingMapsKey = keys['API_keys']['bingMapsKey']

def get_coords(address, zip_code=None):
    """Geocode a mailing address into lat/lon.

    Args:
        zip_code (int): helps with accuracy of results, optional

    Returns: dict of keys lat, lon
    """
    baseurl = r"http://dev.virtualearth.net/REST/v1/Locations"

    url_dict = {
        'countryRegion': 'US',
        'postalCode': zip_code,
        'addressLine': address,
        'inclnb': '1',
        'maxResults': '1',
        'key': bingMapsKey,
        'userLocation': '38.8447476,-77.0519393'  # a general location so it prioritizes results
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(baseurl, params=url_args)
    if response.status_code != 200:
        raise support.BadResponse('Response code from bing not 200.')

    resp_dict = response.json()
    #coords = resp_dict['resourceSets'][0]['resources'][0]['point']['coordinates']  # Rooftop coordinates
    coords = resp_dict['resourceSets'][0]['resources'][0]['geocodePoints'][-1]['coordinates']  # Route coordinates
    coords_dict = dict(zip(('lat', 'lon'), coords))
    return coords_dict


def get_bing_commute_time(startcoords, endcoords):
    """Get commute travel time between two lat/lon tuples from Bing API.

    Parameters
    ----------
    startcoords : iterable
        a list or tuple of geographic coordinates (lat/lon) as integers
    endcoords: iterable
        same as startcoords

    Returns
    -------
    str: (commute_time, first_walk_time), in HH:MM:SS
    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Transit"

    url_dict = {
        'wp.0': support.str_coords(startcoords),
        'wp.1': support.str_coords(endcoords),
        'timeType': 'Arrival',
        'dateTime': support.get_commute_datetime('bing'),
        'distanceUnit': 'mi',
        'key': bingMapsKey
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(baseurl, params=url_args)
    if response.status_code != 200:
        raise support.BadResponse('Response code from bing not 200.')
    r_dict = response.json()

    try:
        travel_time = r_dict['resourceSets'][0]['resources'][0]['travelDuration']
    except KeyError:
        raise support.BadResponse('JSON response does not have travel_time_minutes key.')
    commute_time = round(travel_time/60, 0)

    # Function detour to get walk time of first leg of trip
    itin = r_dict['resourceSets'][0]['resources'][0]['routeLegs'][0]['itineraryItems']
    first_walk_time = 0
    for ix, leg in enumerate(itin):
        if leg.get('iconType') in ['Bus', 'Train']:
            first_walk_time = itin[ix-1]['travelDuration']  # get previous leg, in sec
            first_leg = leg.get('iconType')
            break
    first_walk_time = round(first_walk_time/60, 1)

    return commute_time, first_walk_time, first_leg


def get_walking_info(startcoords, endcoords):
    """Retrieves the walking distance and duration between two
    sets of XY coords.

    :returns (distance, duration) tuple
    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Walking"

    url_dict = {
        'wp.0': support.str_coords(startcoords),
        'wp.1': support.str_coords(endcoords),
        'optimize': 'time',
        'distanceUnit': 'mi',
        'key': bingMapsKey
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(baseurl, params=url_args)
    r_dict = response.json()

    distance = r_dict['resourceSets'][0]['resources'][0]['travelDistance']
    duration = r_dict['resourceSets'][0]['resources'][0]['travelDuration']

    walk_info = {
        'walk_distance_miles': round(distance, 2),
        'walk_time': '{}'.format(str(dt.timedelta(seconds=duration)))
    }
    return walk_info


def find_nearest_metro(startcoords):
    """Given coordinates to a house (or wherever), find the two
    closest metro stations.

    Some metro stations are known to Bing by the name "Metro". In
    these cases, they usually have a good URL so I'm taking the
    name from the WMATA page that references them.

    Returns a list of (name, geocoords) tuples"""
    BASEURL = r"http://dev.virtualearth.net/REST/V1/LocalSearch/"

    url_dict = {
        'query': 'metro station',
        'userLocation': support.str_coords(startcoords),
        'maxResults': 2,
        'key': bingMapsKey
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(BASEURL, params=url_args)

    if response.status_code != 200:
        print('Request for metro stations failed.')
        raise support.BadResponse('Response code for metro stations not 200.')

    r_dict = response.json()
    metro_list = []
    for result in r_dict['resourceSets'][0]['resources']:
        name = result['name']
        if (len(name) < 6) | (name == 'Metro Rail'):
            web = result['Website']
            url_last_slash = web.rfind('/')
            url_page_extension = web.rfind('.')
            name = web[url_last_slash + 1:url_page_extension]
        coords = result['point']['coordinates']
        walk_info = get_walking_info(startcoords, coords)
        metro_list.append(
            {'{}'.format(name.upper()): walk_info}
        )
    sorted_metro_list = sorted(
        metro_list.items(), key=lambda x: x[1].get('walk_dist')
    )
    return dict(sorted_metro_list)


def get_driving_info(startcoords, endcoords, dayofweek=None, hrmin=None):
    """Retrieves the driving distance and duration between two
    sets of XY coords.
    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Driving"
    # Do not pass args if they are not supplied (the function will use its defaults
    #   but really, you should always include a time and day that you'll be driving.
    commute_datetime_args = [x for x in [dayofweek, hrmin] if x is not None]

    url_dict = {
        'wp.0': support.str_coords(startcoords),
        'wp.1': support.str_coords(endcoords),
        'distanceUnit': 'mi',
        'optimize': 'timeWithTraffic',
        'datetime': support.get_commute_datetime('bing', *commute_datetime_args),
        'key': bingMapsKey
        }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(baseurl, params=url_args)
    if response.status_code != 200:
        print('Request for driving time failed.')
        raise support.BadResponse

    r_dict = response.json()
    distance = r_dict['resourceSets'][0]['resources'][0]['travelDistance']
    duration = r_dict['resourceSets'][0]['resources'][0]['travelDuration']
    # pretty print
    distance = '{:.2f} miles'.format(distance)
    duration = str(dt.timedelta(seconds=duration))
    return distance, duration


if __name__ == '__main__':
    SAMPLE_ADDR = '10217 ROLLING GREEN WAY FORT WASHINGTON, MD'
    sample_coords = tuple(get_coords(SAMPLE_ADDR).values())
    sample_commute_time = get_bing_commute_time(sample_coords, keys.work_coords)
    sample_metro = find_nearest_metro(sample_coords)
    sample_drive = get_driving_info(sample_coords, keys.work_coords, 0, '07:00')

    print('Coords: {}'.format(sample_coords))
    print('Commute to work: {}'.format(sample_commute_time))
    print('Nearest metro stations:')
    for i in sample_metro:
        print(i[0], i[1])
