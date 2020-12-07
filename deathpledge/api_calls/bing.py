"""
Update properties retrieved with Bing Maps.
"""

import requests
import datetime as dt
import logging
from collections import namedtuple

from deathpledge import keys
from deathpledge import support

logger = logging.getLogger(__name__)


class BingMapsAPI(object):
    """Container for getting data from Bing Maps REST API."""

    def __init__(self):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self.bingMapsKey = keys['API_keys']['bingMapsKey']

    def get_geocoords(self, geocoder):
        """Geocode a location with the route coordinates of a street address.
        
        Args: 
            geocoder (BingGeocoderAPICall): URL constructor for this API call, containing
                the address to be geocoded.

        Returns:
            Geocoords: latitude and longitude as floats

        """
        api_response = self._get_api_response(geocoder)
        coordinates_value = (api_response.get('resourceSets')[0]
                             .get('resources')[0]
                             .get('geocodePoints')[-1]
                             .get('coordinates'))
        return Geocoords._make(coordinates_value)

    def get_commute(self):
        pass

    def get_nearby_metro(self):
        pass

    def get_driving_info(self):
        pass

    def _get_api_response(self, api_call) -> dict:
        """Sends HTTP request built from url and parameters.

        Args:
            api_call (BingAPICall): Baseurl and parameters.

        Raises:
            support.BadResponse: If Bing does not send back 200 response.

        """
        api_call.url_args['key'] = self.bingMapsKey
        response = requests.get(api_call.baseurl, params=api_call.url_args)
        if response.status_code != 200:
            raise support.BadResponse('Response code from bing not 200.')
        return response.json()


class Geocoords(namedtuple('Coordinates', 'lat lon')):
    """Latitude and longitude for a location on earth."""
    __slots__ = ()

    def to_string(self):
        """For passing to the Bing REST API"""
        return f'{self.lat},{self.lon}'


class BingAPICall(object):
    """Abstract class for constructing HTTP API calls."""
    __slots__ = ('baseurl', 'url_args')


class BingGeocoderAPICall(BingAPICall):
    """Constructs URL args for API call to Bing maps for geocoding a street address.

    Adds a vague userLocation to prioritize results in my area.

    Attributes:
        baseurl (str): URL for this Bing Maps API call.
        url_args (dict): Parameters to be appended to the `baseurl`.

    Args:
        address: Mailing address.
        zip_code (Optional): Helps with accuracy of results. Defaults to None.

    """
    baseurl = r"http://dev.virtualearth.net/REST/v1/Locations"

    def __init__(self, address: str, zip_code: int = None):
        url_args = {
            'countryRegion': 'US',
            'postalCode': zip_code,
            'addressLine': address,
            'inclnb': '1',
            'maxResults': '1',
            'key': None,  # added by BingMapAPI method
            'userLocation': '38.8447476,-77.0519393'
        }
        self.url_args = {k: v for k, v in url_args.items() if v is not None}


def get_bing_commute_time(startcoords, endcoords):
    """Get commute travel time between two lat/lon tuples from Bing API.

    Args:
        startcoords (iterable): a list or tuple of geographic coordinates (lat/lon) as integers
        endcoords (iterable): same as startcoords

    Returns:
        namedtuple:
            commute_time: Total commute time in minutes
            first_leg (str): Mode of transit for first major leg
            first_walk (float): Walk time in minutes to first transit or destination

    Raises:
        BadResponse: If Bing response is not 200.
        KeyError: If JSON from Bing does not match expected structure.

    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Transit"

    url_dict = {
        'wp.0': support.str_coords(startcoords),
        'wp.1': support.str_coords(endcoords),
        'timeType': 'Arrival',
        'dateTime': support.get_commute_datetime('bing'),
        'distanceUnit': 'mi',
        'key': None
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(baseurl, params=url_args)
    if response.status_code != 200:
        raise support.BadResponse('Response code from bing not 200.')
    r_dict = response.json()
    try:
        trip = r_dict['resourceSets'][0]['resources'][0]
    except KeyError:
        raise KeyError('JSON response from Bing does not have expected structure.')

    travel_time_in_sec: int = trip.get('travelDuration')
    travel_time_in_min: float = round(travel_time_in_sec/60, 0)
    try:
        first_leg = get_first_leg_from_trip(trip=trip)
    except ValueError:
        logger.exception('Failed to get first transit leg info.')
        first_leg = {}

    Commute = namedtuple('Commute', ['commute_time', 'first_leg', 'first_walk'])
    commute = Commute(
        commute_time=travel_time_in_min,
        first_leg=first_leg.get('mode'),
        first_walk=first_leg.get('walktime')
    )
    return commute


def get_first_leg_from_trip(trip: dict) -> dict:
    """Get transit mode for first transit leg of journey, and the walk time to it.

    Assume that the first step in trip is always a walk, set that to
    be the first leg mode and walktime. If a bus or train follows in step
    2, update the mode but keep the walk time from original walk.

    Args:
        trip: Commute JSON response from bing.

    Returns:
        mode (str), walktime (float)

    Raises:
        ValueError: If Bing gives a transit type other than walk, bus, or train.

    """
    itinerary = trip['routeLegs'][0]['itineraryItems']
    first_leg = {
        'mode': itinerary[0].get('iconType'),
        'walktime': round(itinerary[0].get('travelDuration') / 60, 1)
    }
    for i, leg in enumerate(itinerary):
        leg_mode = leg.get('iconType')
        if leg_mode == 'Walk':
            continue
        elif leg_mode in ['Bus', 'Train']:
            first_leg.update(dict(mode=leg_mode))
            break
        else:
            raise ValueError(f"Unknown transit mode from Bing:'{leg_mode}'")
    return first_leg


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
        'key': None
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

    Returns:
        list: (name, geocoords) tuples

    Raises:
        BadResponse: If Bing doesn't return response code 200.
    """
    BASEURL = r"http://dev.virtualearth.net/REST/V1/LocalSearch/"

    url_dict = {
        'query': 'metro station',
        'userLocation': support.str_coords(startcoords),
        'maxResults': 2,
        'key': None
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(BASEURL, params=url_args)

    if response.status_code != 200:
        print('Request for metro stations failed.')
        raise support.BadResponse('Response code for metro stations not 200.')

    r_dict = response.json()
    metro_stations = {}
    for result in r_dict['resourceSets'][0]['resources']:
        name = result['name']
        if (len(name) < 6) | (name == 'Metro Rail'):
            web = result['Website']
            url_last_slash = web.rfind('/')
            url_page_extension = web.rfind('.')
            name = web[url_last_slash + 1:url_page_extension]
        coords = result['point']['coordinates']
        walk_info = get_walking_info(startcoords, coords)
        metro_stations.update(
            {'{}'.format(name.upper()): walk_info}
        )
    sorted_metro_list = sorted(
        metro_stations.items(), key=lambda x: x[1].get('walk_distance_miles')
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
        'key': None
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
    full_address = '1600 Pennsylvania Ave NW, Washington, DC 20500'
    zip = 20500
    bing_api = BingMapsAPI()
    gc = BingGeocoderAPICall(address=full_address, zip_code=zip)
    coords = bing_api.get_geocoords(gc)
