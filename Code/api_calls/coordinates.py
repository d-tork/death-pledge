"""Get latitude and longitude for an address from Bing geocode."""

import requests
from Code.api_calls import keys

# Constants
BING_MAPS_KEY = keys.bingMapsKey
BASEURL = r"http://dev.virtualearth.net/REST/v1/Locations"


def get_coords(address, zip_code=None):
    """Geocode a mailing address"""

    url_dict = {
        'countryRegion': 'US',
        'postalCode': zip_code,
        'addressLine': address,
        'inclnb': '1',
        'maxResults': '1',
        'key': BING_MAPS_KEY,
        'userLocation': '38.8447476,-77.0519393'
    }
    url_args = {k: v for k, v in url_dict.items() if v is not None}
    response = requests.get(BASEURL, params=url_args)

    resp_dict = response.json()
    #coords = resp_dict['resourceSets'][0]['resources'][0]['point']['coordinates']  # Rooftop coordinates
    coords = resp_dict['resourceSets'][0]['resources'][0]['geocodePoints'][-1]['coordinates']  # Route coordinates
    return tuple(coords)


if __name__ == '__main__':
    SAMPLE_ADDR = '10217 ROLLING GREEN WAY FORT WASHINGTON, MD'
    SAMPLE_COORDS = get_coords(SAMPLE_ADDR)
    print(SAMPLE_COORDS)
