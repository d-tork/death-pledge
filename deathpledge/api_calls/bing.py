"""
Update properties retrieved with Bing Maps.
"""

import requests
import datetime as dt
import logging
from collections import namedtuple
from functools import lru_cache

from deathpledge import keys
from deathpledge import support

logger = logging.getLogger(__name__)


class BingFailure(Exception):
    pass


class BingMapsAPI(object):
    """Container for getting data from Bing Maps REST API."""

    def __init__(self):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self.bingMapsKey = keys['API_keys']['bingMapsKey']

    @lru_cache()
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

    def get_commute(self, commute_request):
        """Get commute travel time between two lat/lon tuples from Bing API.

        Args:
            commute_request (BingCommuteAPICall): URL constructor for this API call, containing
                the start and end coordinates.

        Returns:
            namedtuple:
                commute_time: Total commute time in minutes
                first_leg (str): Mode of transit for first major leg
                first_walk (float): Walk time in minutes to first transit or destination

        Raises:
            KeyError: If JSON from Bing does not match expected structure.

        """
        api_response = self._get_api_response(commute_request)
        try:
            trip = api_response['resourceSets'][0]['resources'][0]
        except KeyError:
            raise KeyError('JSON response from Bing does not have expected structure.')

        travel_time_in_sec: int = trip.get('travelDuration')
        travel_time_in_min: float = round(travel_time_in_sec / 60, 0)
        try:
            first_leg = self._get_first_leg_from_trip(trip=trip)
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

    @staticmethod
    def _get_first_leg_from_trip(trip: dict) -> dict:
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

    def get_nearby_metro(self, metro_request, homecoords):
        """Get metro stations nearest a location from Bing API.

        Args:
            metro_request (BingNearbyMetroAPICall): URL constructor for this API call, containing
                the start coordinates.
            homecoords (Geocoords): Start coordinates for creating the walk time request.

        Returns:
            dict: {metro station: walk info}

        Raises:
            KeyError: If JSON from Bing does not match expected structure.

        """
        api_response = self._get_api_response(metro_request)
        metro_stations = {}
        for result in api_response['resourceSets'][0]['resources']:
            name = result['name']
            if (len(name) < 6) | (name == 'Metro Rail'):
                web = result['Website']
                url_last_slash = web.rfind('/')
                url_page_extension = web.rfind('.')
                name = web[url_last_slash + 1:url_page_extension]
            station_coords = Geocoords._make(result['point']['coordinates'])
            walk_request = BingWalkAPICall(
                startcoords=homecoords,
                endcoords=station_coords
            )
            walk_info = self.get_walk_time(walk_request=walk_request)
            metro_stations.update(
                {'{}'.format(name.upper()): dict(
                    distance=walk_info.distance, duration=walk_info.duration
                )}
            )
        sorted_metro_list = sorted(
            metro_stations.items(), key=lambda x: x[1].get('distance')
        )
        return dict(sorted_metro_list)

    def get_walk_time(self, walk_request):
        """Retrieves the walking distance and duration between two sets of coords.

        Args:
            walk_request (BingWalkAPICall): URL constructor for this API call, containing
                the start and end coordinates.

        Returns:
            namedtuple:
                distance (float): Walk distance to destination in miles
                duration (int): Walk time to destination

        """
        api_response = self._get_api_response(walk_request)
        distance = api_response['resourceSets'][0]['resources'][0]['travelDistance']
        duration = api_response['resourceSets'][0]['resources'][0]['travelDuration']
        Walk = namedtuple('Walk', 'distance duration')
        walk = Walk(
            distance=round(distance, 2),
            duration='{}'.format(str(dt.timedelta(seconds=duration)))
        )
        return walk

    def get_driving_info(self, driving_request):
        """Retrieves the walking distance and duration between two sets of coords.

        Args:
            driving_request (BingDrivingAPICall): URL constructor for this API call, containing
                the start and end coordinates.

        Returns:
            namedtuple:
                distance (float): Drive distance to destination in miles
                duration (int): Drive time to destination

        """
        api_response = self._get_api_response(driving_request)
        distance = api_response['resourceSets'][0]['resources'][0]['travelDistance']
        duration = api_response['resourceSets'][0]['resources'][0]['travelDuration']
        Drive = namedtuple('Drive', 'distance duration')
        drive = Drive(
            distance='{:.2f} miles'.format(distance),
            duration=str(dt.timedelta(seconds=duration))
        )
        return drive

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


class BingCommuteAPICall(BingAPICall):
    """Constructs URL args for API call to Bing maps for commute time between two locations.

    Attributes:
        baseurl (str): URL for this Bing Maps API call.
        url_args (dict): Parameters to be appended to the `baseurl`.

    Args:
        startcoords (Geocoords): a namedtuple of geographic coordinates (lat/lon) as integers
        endcoords (Geocoords): same as startcoords

    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Transit"

    def __init__(self, startcoords, endcoords):
        url_args = {
            'wp.0': startcoords.to_string(),
            'wp.1': endcoords.to_string(),
            'timeType': 'Arrival',
            'dateTime': support.get_commute_datetime('bing'),
            'distanceUnit': 'mi',
            'key': None,  # added by BingMapAPI method
        }
        self.url_args = {k: v for k, v in url_args.items() if v is not None}


class BingNearbyMetroAPICall(BingAPICall):
    """Constructs URL args for API call to Bing maps for nearby metro stations.

    Attributes:
        baseurl (str): URL for this Bing Maps API call.
        url_args (dict): Parameters to be appended to the `baseurl`.

    Args:
        startcoords (Geocoords): a namedtuple of geographic coordinates (lat/lon) as integers

    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/LocalSearch/"

    def __init__(self, startcoords):
        url_args = {
            'query': 'metro station',
            'userLocation': startcoords.to_string(),
            'maxResults': 2,
            'key': None,  # added by BingMapAPI method
        }
        self.url_args = {k: v for k, v in url_args.items() if v is not None}


class BingWalkAPICall(BingAPICall):
    """Constructs URL args for API call to Bing maps for walk time between two locations.

    Attributes:
        baseurl (str): URL for this Bing Maps API call.
        url_args (dict): Parameters to be appended to the `baseurl`.

    Args:
        startcoords (Geocoords): a namedtuple of geographic coordinates (lat/lon) as integers
        endcoords (Geocoords): same as startcoords

    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Walking"

    def __init__(self, startcoords, endcoords):
        url_args = {
            'wp.0': startcoords.to_string(),
            'wp.1': endcoords.to_string(),
            'optimize': 'time',
            'distanceUnit': 'mi',
            'key': None,  # added by BingMapAPI method
        }
        self.url_args = {k: v for k, v in url_args.items() if v is not None}


class BingDrivingAPICall(BingAPICall):
    """Constructs URL args for API call to Bing maps for driving time and distance between two locations.

    Attributes:
        baseurl (str): URL for this Bing Maps API call.
        url_args (dict): Parameters to be appended to the `baseurl`.

    Args:
        startcoords (Geocoords): a namedtuple of geographic coordinates (lat/lon) as integers
        endcoords (Geocoords): same as startcoords
        dayofweek (int): Day of the week of expected driving, where 0 = Monday
        hrmin (str): Time of expected driving, as 24-hour clock, e.g. '16:00'

    """
    baseurl = r"http://dev.virtualearth.net/REST/V1/Routes/Driving"

    def __init__(self, startcoords, endcoords, dayofweek=None, hrmin=None):
        commute_datetime_args = [x for x in [dayofweek, hrmin] if x is not None]
        url_args = {
            'wp.0': startcoords.to_string(),
            'wp.1': endcoords.to_string(),
            'optimize': 'timeWithTraffic',
            'distanceUnit': 'mi',
            'datetime': support.get_commute_datetime('bing', *commute_datetime_args),
            'key': None,  # added by BingMapAPI method
        }
        self.url_args = {k: v for k, v in url_args.items() if v is not None}


class BingDataGetter(object):
    """Adds Bing maps attributes to a home."""

    def __init__(self, home):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self.home = home
        self.bing_api = BingMapsAPI()

    def add_data_to_home(self):
        if not self.home.get('geocoords'):
            self._get_home_coordinates()
        self._get_commute()
        self._get_nearby_metro()
        self._get_driving()

    def _get_home_coordinates(self):
        geocoder = BingGeocoderAPICall(
            address=self.home.get('full_address'),
            zip_code=self.home.get('parsed_address').get('ZipCode')
        )
        try:
            self.home['geocoords'] = self.bing_api.get_geocoords(geocoder=geocoder)
        except support.BadResponse:
            raise BingFailure(f"Could not retrieve geocoords for {self.home['full_address']}")

    def _get_commute(self):
        commute_request = BingCommuteAPICall(
            startcoords=self.home['geocoords'],
            endcoords=Geocoords._make(keys['Locations']['work_coords'].values())
        )
        try:
            commute = self.bing_api.get_commute(commute_request=commute_request)
        except support.BadResponse:
            self.logger.exception(f"Could not get commute for {self.home['full_address']}")
        else:
            self.home.update({
                'commute_time': commute.commute_time,
                'first_leg': commute.first_leg,
                'first_walk': commute.first_walk
            })

    def _get_nearby_metro(self):
        nearby_metro_request = BingNearbyMetroAPICall(startcoords=self.home['geocoords'])
        try:
            self.home['nearby_metro'] = self.bing_api.get_nearby_metro(
                metro_request=nearby_metro_request,
                homecoords=self.home['geocoords']
            )
        except support.BadResponse:
            self.logger.exception(f"Could not get nearby metro for {self.home['full_address']}")

    def _get_driving(self):
        for place, attribs in keys['Locations']['favorite_driving'].items():
            place_geocoder = BingGeocoderAPICall(address=attribs['addr'])
            place_coords = self.bing_api.get_geocoords(geocoder=place_geocoder)
            driving_request = BingDrivingAPICall(
                startcoords=self.home['geocoords'],
                endcoords=place_coords,
                dayofweek=attribs.get('day'),
                hrmin=attribs.get('time')
            )
            try:
                drive = self.bing_api.get_driving_info(driving_request)
            except support.BadResponse:
                continue
            else:
                self.home.update({
                    f'{place}_dist': drive.distance,
                    f'{place}_time': drive.duration
                })
