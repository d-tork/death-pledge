import os
import glob
from Code.api_calls import bing, citymapper, keys
from Code import json_handling, scrape2, LISTINGS_GLOB
from Code.support import BadResponse


def add_full_addr(dic):
    """Combine address and city_state into full address"""
    full_addr = ' '.join([dic['info']['address'], dic['info']['city_state']])
    dic['info']['full_address'] = full_addr


def add_coords(dic):
    """Add geocoords to house dictionary"""
    # Grab coordinates from Bing
    addr = dic['info']['full_address']
    coords = bing.get_coords(addr, zip_code=addr[-5:])

    # Add to dictionary
    dic['_metadata'] = dic.get('_metadata', {})
    dic['_metadata'].update({'geocoords': coords})
    # Ensure other dictionaries exist
    dic['Local Travel'] = dic.get('Local Travel', {})


def add_citymapper_commute(dic):
    """Add the citymapper transit time for work to the listing dict"""
    house_coords = dic['_metadata']['geocoords']
    try:
        cmtime = citymapper.get_citymapper_commute_time(house_coords, keys.work_coords)
    except BadResponse:
        cmtime = 'Unavailable'
    finally:
        dic['Local Travel']['citymapper_commute'] = str(cmtime)


def add_bing_commute(dic):
    """Add the bing transit time to listing dict"""
    house_coords = dic['_metadata']['geocoords']
    try:
        bingtime = bing.get_bing_commute_time(house_coords, keys.work_coords)
    except BadResponse:
        bingtime = 'Unavailable'
    finally:
        dic['external']['bing_commute'] = str(bingtime)


def add_nearest_metro(dic):
    """Add the three nearest metro stations in distance order"""
    house_coords = dic['_metadata']['geocoords']
    try:
        station_list = bing.find_nearest_metro(house_coords)
    except BadResponse:
        station_list = ['Unavailable']
    finally:
        dic['external']['metro_stations'] = station_list


def add_frequent_driving(dic, favorites_dic):
    """Add the road distance and drive time to frequented places by car."""
    house_coords = dic['_metadata']['geocoords']
    for place, attribs in favorites_dic.items():
        place_coords = bing.get_coords(attribs['addr'])
        day = attribs.get('day', None)
        starttime = attribs.get('time', None)
        try:
            distance, duration = bing.get_driving_info(house_coords, place_coords, day, starttime)
        except BadResponse:
            station_list = ('Unavailable', 'Unavailable')
        finally:
            dic['Local Travel'][place] = (distance, duration)


def sample():
    sample_file = os.path.join('..', 'Data', 'Processed', 'saved_listings',
                               '3008_GALLOP_WAY.json')
    sample_house = json_handling.read_dicts_from_json(sample_file)[0]
    add_coords(sample_house)
    _ = scrape2.add_dict_to_file(sample_house)


def main():
    for f in glob.glob(LISTINGS_GLOB):
        house = json_handling.read_dicts_from_json(f)[0]

        # Add modifying functions here:
        add_full_addr(house)
        add_coords(house)
        add_citymapper_commute(house)
        add_bing_commute(house)
        add_nearest_metro(house)
        add_frequent_driving(house, keys.favorites_driving)

        # Write back out
        _ = scrape2.add_dict_to_file(house)


if __name__ == '__main__':
    # sample()
    main()
