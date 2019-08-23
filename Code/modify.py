import os
import glob
from time import sleep
from Code.api_calls import bing, citymapper, keys
from Code import json_handling, LISTINGS_GLOB
from Code.support import BadResponse


def update_dict(dic, keys_tuple, value):
    """Safely add or update any value in house dict.

    Args:
        dic (dict): house dictionary
        keys_tuple (tuple): a tuple of (category, field)
        value (str, int, float, iterable): whatever's being stored

    """
    # Check if outer key (category) exists; if not, create it
    dic.setdefault(keys_tuple[0], {})
    # Update with new {field: value}
    dic[keys_tuple[0]].update({keys_tuple[1]: round(value, 1)})


def add_full_addr(dic):
    """Combine address and city_state into full address"""
    full_addr = ' '.join([dic['info']['address'], dic['info']['city_state']])
    update_dict(dic, ('info', 'full_address'), full_addr)


def add_coords(dic):
    """Add geocoords to house dictionary"""
    # Grab coordinates from Bing
    addr = dic['info']['full_address']
    coords = bing.get_coords(addr, zip_code=addr[-5:])
    update_dict(dic, ('_metadata', 'geocoords'), coords)


def add_citymapper_commute(dic, force=False):
    """Add the citymapper transit time for work to the listing dict.

    Sleeps because of the API limits.
    """
    key_name = 'Work commute (Citymapper)'
    if key_name not in dic['Local Travel']:
        force = True
    elif dic['Local Travel'][key_name] == 'Unavailable':
        force = True
    else:  # It's in the dict as a real value, defer to force parameter
        pass

    if force:
        house_coords = dic['_metadata']['geocoords']
        try:
            cmtime = citymapper.get_citymapper_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            print(e)
            cmtime = 'Unavailable'
        finally:
            update_dict(dic, ('Local Travel', key_name), str(cmtime))
            print('\tSleeping for 90 seconds')
            sleep(90)
    else:
        print('\tCitymapper commute time already exists. Use force=True to override.')
        return


def add_bing_commute(dic):
    """Add the bing transit time to listing dict"""
    house_coords = dic['_metadata']['geocoords']
    try:
        bingtime = bing.get_bing_commute_time(house_coords, keys.work_coords)
    except BadResponse as e:
        print(e)
        bingtime = 'Unavailable'
    finally:
        dic['Local Travel']['Work commute (Bing)'] = str(bingtime)
        update_dict(dic, ('Local Travel', 'Work commute (Bing)'), str(bingtime))


def add_nearest_metro(dic):
    """Add the three nearest metro stations in distance order"""
    house_coords = dic['_metadata']['geocoords']
    try:
        station_list = bing.find_nearest_metro(house_coords)
    except BadResponse:
        station_list = ['Unavailable']
    finally:
        dic['Local Travel']['Nearby Metro on foot'] = station_list
        update_dict(dic, ('Local Travel', 'Nearby Metro on foot'), station_list)


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
            update_dict(dic, ('Local Travel', place), (distance, duration))


def sample():
    sample_file = os.path.join('..', 'Data', 'Processed', 'saved_listings',
                               '13406_PISCATAWAY_DR.json')
    sample_house = json_handling.read_dicts_from_json(sample_file)[0]
    add_citymapper_commute(sample_house)
    _ = json_handling.add_dict_to_json(sample_house)


def main():
    for f in glob.glob(LISTINGS_GLOB):
        house = json_handling.read_dicts_from_json(f)[0]
        print(os.path.basename(f))

        # Add modifying functions here:
        add_full_addr(house)
        add_coords(house)
        # add_citymapper_commute(house)
        add_bing_commute(house)
        add_nearest_metro(house)
        add_frequent_driving(house, keys.favorites_driving)

        # Write back out
        _ = json_handling.add_dict_to_json(house)


def citymapper_only():
    for f in glob.glob(LISTINGS_GLOB):
        house = json_handling.read_dicts_from_json(f)[0]
        print(os.path.basename(f))
        add_citymapper_commute(house)
        # Write back out
        _ = json_handling.add_dict_to_json(house)


if __name__ == '__main__':
    # sample()
    # citymapper_only()

    file_list = [
        '800_BRAEBURN_DR.json',
        '4689_LAWTON_WAY_201.json',
        '5074_DONOVAN_DR_104.json',
        '5505_SEMINARY_RD_305N.json',
        '5663_HARRINGTON_FALLS_LN_E.json',
        '6172_MORNING_GLORY_RD.json',
        '6325C_EAGLE_RIDGE_LN_31.json',
        '6551_GRANGE_LN_302.json',
        '6614_CUSTER_ST.json',
        '6921_MARY_CAROLINE_CIR_L.json',
    ]
    main()
