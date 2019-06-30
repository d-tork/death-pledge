import requests
import datetime as dt
import keys
import coordinates
import support

baseurl = r'https://developer.citymapper.com/api/1/traveltime/'
url_args = {
    'startcoord': support.str_coords(coordinates.coords),
    'endcoord': support.str_coords(keys.work_coords),
    'time': keys.get_commute_datetime(),
    'time_type': 'arrival',
    'key': keys.citymapperKey
}
response = requests.get(baseurl, params=url_args)
print(response.url)
r_dict = response.json()
travel_time = str(dt.timedelta(minutes=r_dict['travel_time_minutes']))
print(travel_time)
