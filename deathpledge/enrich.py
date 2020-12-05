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

from deathpledge import support, cleaning, keys
from deathpledge.api_calls import bing
from deathpledge.support import BadResponse

logger = logging.getLogger(__name__)


class EnrichError(Exception):
    """Anything gone wrong with an enrichment step, log and continue."""
    pass


def add_coords(home, force=False):
    """Convert address to geocoords."""
    # Check for existing value
    coords = home.setdefault('geocoords', None)
    if (coords is None) or force:
        try:
            coords = bing.get_coords(
                home['full_address'],
                zip_code=home['parsed_address'].get('ZipCode')
            )
        except BadResponse:
            logger.exception(f"Failed to retrieve geocoords for {home.get('address')}")
            coords = None
        else:
            logger.debug('Geocoords updated from Bing')
    home['geocoords'] = coords


def add_bing_commute(home, force=False):
    """Add the bing transit time.

    Existing values are obtained from the home dict. If at least one of them
    is empty or if forced, the Bing API call is made. If not, the values are
    not updated.

    """
    bing_commute_items = {
        'work_commute': None,
        'first_walk_mins': None,
        'first_leg_type': None
    }
    bing_commute_items = {k: home.get(k) for k in bing_commute_items.keys()}

    if (not all([v for k, v in bing_commute_items.items()])) | force:
        # At least one of them is empty or force=True, Bing API call is necessary
        # If not force, and if all values already exist, do not update
        house_coords = tuple(home['geocoords'].values())
        work_coords = tuple(keys['Locations']['work_coords'].values())
        try:
            commute = bing.get_bing_commute_time(
                startcoords=house_coords,
                endcoords=work_coords)
        except (BadResponse, KeyError):
            logger.exception(f"Failed to retrieve Bing commute time for {home.get('address')}")
        else:
            bing_commute_items['work_commute'] = commute.commute_time
            bing_commute_items['first_leg_type'] = commute.first_leg
            bing_commute_items['first_walk_mins'] = commute.first_walk
            home.update(bing_commute_items)
            logger.debug('Commute updated from Bing')


def add_nearest_metro(home):
    """Add the three nearest metro stations in distance order.
    """
    house_coords = tuple(home['geocoords'].values())
    try:
        station_list = bing.find_nearest_metro(house_coords)
    except BadResponse:
        logger.exception(f"Failed to add nearest metro stations for {home.get('address')}")
    else:
        home['nearby_metro'] = station_list


def add_frequent_driving(home, favorites_dic):
    """Add the road distance and drive time to frequented places by car.
    TODO: refactor
    """
    house_coords = tuple(home['geocoords'].values())
    for place, attribs in favorites_dic.items():
        place_coords = tuple(bing.get_coords(attribs['addr']).values())
        day = attribs.get('day', None)
        starttime = attribs.get('time', None)
        try:
            distance, duration = bing.get_driving_info(house_coords, place_coords, day, starttime)
        except BadResponse:
            continue
        else:
            home[f'{place}_dist'] = distance
            home[f'{place}_time'] = duration
            logger.debug('Frequent driving added')


def add_tether(home):
    """Add straight-line distance to centerpoint."""
    house_coords = tuple(home['geocoords'].values())
    center = tuple(keys['Locations']['centerpoint'].values())
    try:
        dist = support.haversine(house_coords, center)
    except:
        logger.exception('Failed to add tether')
    else:
        home['tether'] = round(dist, 2)
