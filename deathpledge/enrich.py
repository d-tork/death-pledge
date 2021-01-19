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
import logging

from deathpledge import support, keys
from deathpledge.api_calls import bing

logger = logging.getLogger(__name__)


class EnrichError(Exception):
    """Anything gone wrong with an enrichment step, log and continue."""
    pass


def add_bing_maps_data(home):
    """Return all data from Bing maps for a given home."""
    bing_getter = bing.BingDataGetter(home)
    bing_getter.add_data_to_home()


def add_tether(home):
    """Add straight-line distance to centerpoint."""
    house_coords = tuple(home['geocoords'])
    center = tuple(keys['Locations']['centerpoint'].values())
    try:
        dist = support.haversine(house_coords, center)
    except:
        logger.exception('Failed to add tether')
    else:
        home['tether'] = round(dist, 2)
