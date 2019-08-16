import os
import glob
from Code.api_calls import coordinates, citymapper
from Code import json_handling, scrape2, LISTINGS_GLOB


def add_coords(dic):
    """Add geocoords to house dictionary"""
    # Grab coordinates from Bing
    addr = dic['info']['full_address']
    coords = coordinates.get_coords(addr, zip_code=addr[-5:])
    print('{} --> {}'.format(addr, coords))

    # Add to dictionary
    dic['external'] = dic.get('external', {})
    dic['external'].update({'geocoords': coords})


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
        add_coords(house)

        # Write back out
        _ = scrape2.add_dict_to_file(house)


if __name__ == '__main__':
    # sample()
    main()
