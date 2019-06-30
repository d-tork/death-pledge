"""Get latitude and longitude for an address from Bing geocode."""

import requests
import keys

# Your Bing Maps Key
bingMapsKey = keys.bingMapsKey

# input information
address_line = '6541 GRANGE LN #201'
address_zip = '22315'

baseurl = r"http://dev.virtualearth.net/REST/v1/Locations"
url_args = {
    'countryRegion': 'US',
    'postalCode': address_zip,
    'addressLine': address_line,
    'inclnb': '1',
    'maxResults': '1',
    'key': bingMapsKey,
    'userLocation': '38.8447476,-77.0519393'
}
response = requests.get(baseurl, params=url_args)
print(response.url)

resp_dict = response.json()
coords = resp_dict['resourceSets'][0]['resources'][0]['point']['coordinates']
print(coords)

