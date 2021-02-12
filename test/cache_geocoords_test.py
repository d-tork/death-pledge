from deathpledge.api_calls import bing
from deathpledge import keys
from functools import lru_cache

locations = keys['Locations']['favorite_driving']
addresses = [v['addr'] for _, v in locations.items()]
bing_api = bing.BingMapsAPI()


@lru_cache()
def get_coords():
    for addr in addresses:
        gc = bing.BingGeocoderAPICall(address=addr)
        bing_api.get_geocoords(gc)


if __name__ == '__main__':
    import timeit

    print(timeit.timeit('get_coords()', globals=globals(), number=10))
