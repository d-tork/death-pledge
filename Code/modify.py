import os
import glob
from time import sleep
import Code
from Code import json_handling, support
from Code.api_calls import bing, citymapper, keys
from Code.support import BadResponse


def update_house_dict(dic, keys_tuple, value):
    """Safely add or update any value in house dict.

    Args:
        dic (dict): house dictionary
        keys_tuple (tuple): a tuple of (category, field)
        value (str, int, float, iterable): whatever's being stored

    """
    # Check if outer key (category) exists; if not, create it
    dic.setdefault(keys_tuple[0], {})
    # Update with new {field: value}
    dic[keys_tuple[0]].update({keys_tuple[1]: value})


def rename_key(dic, old, new, level):
    if level == 1:
        dic[new] = dic.pop(old)
    elif level == 2:
        for k, v in dic.items():
            try:
                v[new] = v.pop(old)
            except KeyError:
                continue
    else:
        raise ValueError("Not a valid level in the dictionary.")


def add_coords(dic, force=False):
    """Add geocoords to house dictionary"""
    # Check for existing value
    coords = dic['_metadata'].setdefault('geocoords', None)
    if (coords is None) or force:
        print('TESTING: getting coords')
        # Grab coordinates from Bing
        addr = dic['_info']['full_address']
        coords = bing.get_coords(addr, zip_code=addr[-5:])
        update_house_dict(dic, ('_metadata', 'geocoords'), coords)
    else:
        print('TESTING: *not* getting coords')


def add_citymapper_commute(dic, force=False):
    """Add the citymapper transit time for work to the listing dict.

    Raises a sleep reminder exception because of the API limits. When
    using this function on a single listing, catch the exception but
    let it pass. However, when running in a loop of multiple listings,
    catch it and let the program sleep for 90 seconds.
    """
    key_name = 'Work commute (Citymapper)'
    # Check for existing value
    cmtime = dic['local travel'].setdefault(key_name, None)
    if (cmtime is None) or force:
        house_coords = dic['_metadata']['geocoords']
        try:
            cmtime = citymapper.get_citymapper_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            print(e)
            cmtime = None
        finally:
            update_house_dict(dic, ('local travel', key_name), str(cmtime))
            raise citymapper.Sleepytime
    else:
        print('\tCitymapper commute time already exists. Use force=True to override.')
        return


def add_bing_commute(dic, force=False):
    """Add the bing transit time to listing dict"""
    # Check for existing value
    bingtime = dic['local travel'].setdefault('Work commute (Bing)', None)
    if (bingtime is None) or force:
        print('TESTING: getting bing commute')
        house_coords = dic['_metadata']['geocoords']
        try:
            bingtime = bing.get_bing_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            print(e)
            bingtime = 'Unavailable'
        finally:
            update_house_dict(dic, ('local travel', 'Work commute (Bing)'), str(bingtime))
    else:
        print('TESTING: *not* getting bing commute')


def add_nearest_metro(dic, force=False):
    """Add the three nearest metro stations in distance order"""
    # Check for existing value
    station_list = dic['local travel'].setdefault('Nearby Metro', None)
    if (station_list is None) or force:
        print('TESTING: getting nearest metro')
        house_coords = dic['_metadata']['geocoords']
        try:
            station_list = bing.find_nearest_metro(house_coords)
        except BadResponse:
            station_list = None
        finally:
            update_house_dict(dic, ('local travel', 'Nearby Metro'), station_list)
    else:
        print('TESTING: *not* getting bing commute')


def add_frequent_driving(dic, favorites_dic, force=False):
    """Add the road distance and drive time to frequented places by car."""
    house_coords = dic['_metadata']['geocoords']
    for place, attribs in favorites_dic.items():
        # Check for existing value
        place_coords = dic['local travel'].setdefault(place, None)
        if (place_coords is None) or force:
            print('TESTING: getting {} coords'.format(place))
            place_coords = bing.get_coords(attribs['addr'])
            day = attribs.get('day', None)
            starttime = attribs.get('time', None)
            try:
                distance, duration = bing.get_driving_info(house_coords, place_coords, day, starttime)
            except BadResponse:
                distance, duration = ('Unavailable', 'Unavailable')
            finally:
                update_house_dict(dic, ('local travel', place), (distance, duration))
        else:
            print('TESTING: *not* getting place coords')


def travel_quick_stats(dic):
    """Convert some Local Travel numbers for easier scoring."""
    # Grab top metro station's time
    metro = dic['local travel'].get('Nearby Metro')  # returns list of multiple [station, (dist, time)]
    metro_mins = support.str_time_to_min(metro[0][1][1])  # subscripting: first station > values tuple > time

    # Grab bing commute time
    commute = dic['local travel'].get('Work commute (Bing)')
    commute_mins = support.str_time_to_min(commute)

    # Add to new dict
    update_house_dict(dic, ('quickstats', 'metro_walk_mins'), round(metro_mins, 1))
    update_house_dict(dic, ('quickstats', 'commute_transit_mins'), round(commute_mins, 1))


def single(filename):
    print(filename)
    filepath = os.path.join(Code.LISTINGS_DIR, filename)
    house = json_handling.read_dicts_from_json(filepath)[0]

    # Add modifying functions here:
    add_coords(house)
    try:
        add_citymapper_commute(house)
    except citymapper.Sleepytime:
        pass
    add_bing_commute(house)
    add_nearest_metro(house)
    add_frequent_driving(house, keys.favorites_driving)
    travel_quick_stats(house)

    # Write back out
    _ = json_handling.add_dict_to_json(house)


def main():
    for f in glob.glob(Code.LISTINGS_GLOB):
        print(f)
        filepath = os.path.join(Code.LISTINGS_DIR, f)
        house = json_handling.read_dicts_from_json(filepath)[0]

        # Add modifying functions here:
        add_coords(house)
        try:
            add_citymapper_commute(house)
        except citymapper.Sleepytime:
            print('sleeping for 90 seconds.')
            sleep(90)
        add_bing_commute(house)
        add_nearest_metro(house)
        add_frequent_driving(house, keys.favorites_driving)
        travel_quick_stats(house)

        # Write back out
        _ = json_handling.add_dict_to_json(house)


def citymapper_only():
    for f in glob.glob(Code.LISTINGS_GLOB):
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
    # main()
    single('4304_34TH_ST_S_B2.json')
