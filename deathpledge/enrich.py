"""
Module for modifying the contents of a house listing dictionary.

The majority of these functions are dedicated to adding the values
and attributes that come from external data sources, or else are
transformations of existing attributes, post-scraping.

TODO: add these calculations
- bing commute
- nearest metro
- frequent driving
- travel quick stats
- sale price diff
- tether
- days on market
- change from initial
- tax assessed difference
"""
from datetime import datetime as dt
import logging

from deathpledge import support, cleaning
from deathpledge.api_calls import bing, keys
from deathpledge.support import BadResponse

logger = logging.getLogger(__name__)


def add_coords(home, force=False):
    """Convert address to geocoords."""
    # Check for existing value
    coords = home.setdefault('geocoords', None)
    if (coords is None) or force:
        # Grab coordinates from Bing
        try:
            coords = bing.get_coords(
                home.full_address,
                zip_code=home['parsed_address'].get('ZipCode')
            )
        except BadResponse as e:
            print(f'Could not retrieve geocoords for this address: \n{e}')
            coords = None
    home['geocoords'] = coords


def add_bing_commute(home, force=False):
    """Add the bing transit time."""
    bing_commute_items = {
        'work_commute': None,
        'first_walk_mins': None,
        'first_leg_type': None
    }
    bing_commute_items = {k: home.get(k) for k in bing_commute_items.keys()}

    if (not all([v for k, v in bing_commute_items.items()])) | force:
        # At least one of them is empty or force=True, Bing API call is necessary
        # If not force, and if all values exist, then end function
        house_coords = home.get_geocoords()
        house_coords = (house_coords['lat'], house_coords['lon'])
        try:
            commute, walk_time, leg_type = bing.get_bing_commute_time(house_coords, keys.work_coords)
        except BadResponse as e:
            logger.info(f'Could not retrieve Bing commute time for {home.full_address}.\n{e}')
            commute, walk_time, leg_type = '', '', ''
        finally:
            bing_commute_items['work_commute'] = commute
            bing_commute_items['first_walk_mins'] = walk_time
            bing_commute_items['first_leg_type'] = leg_type
            home.update(bing_commute_items)


def add_nearest_metro(dic, force=False):
    """Add the three nearest metro stations in distance order.
    TODO: refactor
    """
    # Check for existing value
    station_list = dic['local travel'].setdefault('Nearby Metro', None)
    if (station_list is None) or force:
        house_coords = tuple(dic['main']['geocoords'].values())
        try:
            station_list = bing.find_nearest_metro(house_coords)
        except BadResponse as e:
            print(e)
            station_list = None
        finally:
            return station_list


def add_frequent_driving(dic, favorites_dic, force=False):
    """Add the road distance and drive time to frequented places by car.
    TODO: refactor
    """
    house_coords = tuple(dic['main']['geocoords'].values())
    for place, attribs in favorites_dic.items():
        # Check for existing value
        place_coords = dic['local travel'].setdefault(place, None)
        if (place_coords is None) or force:
            place_coords = bing.get_coords(attribs['addr'])
            day = attribs.get('day', None)
            starttime = attribs.get('time', None)
            try:
                distance, duration = bing.get_driving_info(house_coords, place_coords, day, starttime)
            except BadResponse:
                distance, duration = None
            finally:
                return distance, duration


def travel_quick_stats(dic):
    """Convert some Local Travel numbers for easier scoring."""
    # Grab top metro station's time
    metro = dic['local travel'].get('Nearby Metro')  # returns list of multiple [station, (dist, time)]
    metro_mins = support.str_time_to_min(metro[0][1][1])  # subscripting: first station > values tuple > time

    # Grab bing commute time
    commute = dic['local travel'].get('Work commute (Bing)')
    commute_mins = support.str_time_to_min(commute)

    return round(metro_mins, 1), round(commute_mins, 1)


def add_tether(dic):
    """Add straight-line distance to centerpoint (Arlington Cememtery)."""
    house_coords = dic['_metadata'].get('geocoords')
    center = keys.centerpoint
    try:
        dist = support.haversine(house_coords, center)
    except TypeError:
        print('\tDistance from center not added; missing house coords.')
    return round(dist, 2)


def update_days_on_market(dic):
    """Calculate days from initial listing to last modification date of dict."""
    start_date, end_date = None, dt.today()
    # Find day of initial listing
    for date, text in dic['listing history'].items():
        if 'Sold' in text:
            end_date = dt.strptime(date, '%b %d, %Y')
        elif 'Initial' in text:
            start_date = dt.strptime(date, '%b %d, %Y')
    try:
        dom = (end_date - start_date).days
        return dom
    except TypeError:
        print('\tListing date not found in history.')
        return


def change_from_initial(dic):
    """Calculate the change from the initial price."""
    # Get current price
    current_price = dic['_info'].get('list_price')

    # Find initial listing
    for date, text in dic['listing history'].items():
        if 'Initial' in text:
            initial_price = text.split()[3]
            initial_price = cleaning.currency_to_int(initial_price)

    price_diff = current_price - initial_price
    if price_diff != 0:
        pct_change = '{:+.1%}'.format(price_diff / initial_price)
    return price_diff, pct_change


def sale_price_diff(dic):
    """Get the difference between listing price and sale price."""
    info = dic['_info']
    if info.get('badge') == 'Sold':
        list_price = info.get('list_price')
        sale_price = info.get('sale_price')
        diff = sale_price - list_price
        diff_pct = '{:.1%}'.format(diff / list_price)
    return diff, diff_pct


def tax_assessed_diff(dic):
    """Get the difference between listing price and the tax assessed value."""
    list_price = dic['_info'].get('list_price')
    tax_assessed = dic['expenses / taxes'].get('Tax Assessed Value')
    diff = tax_assessed - list_price
    diff_pct = '{:.1%}'.format(diff / list_price)
    return diff_pct


if __name__ == '__main__':
    pass
