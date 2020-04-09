"""Class definitions for death-pledge."""

from datetime import datetime
from os import path
import json
import warnings

import Code
from Code import scrape2, database, support


class House(dict):
    """Container for a property's attributes.

    Instances can be created given an address (which will be standardized) OR
    a URL to the RealScout listing OR neither. The idea is that instances can
    be created from houses that are *not* listed on the market, for comparison
    purposes. In those cases, the attributes can't be scraped and will need to
    be manually added.

    The house's ID (for DB purposes) is a SHA-1 hash in hex format of the
    address string like so:
        123 North Maple Dr. #456 --> 123 NORTH MAPLE DR 456 --> ac5e4a2jh10...

    A filename for local storage is the address slugified, but with underscores
    and all uppercase:
        123_NORTH_MAPLE_DR_456.json

    Attributes:
        doctype (str): type of document to store
    """
    doctype = 'house'

    def __init__(self, address=None, url=None, added_date=None):
        super().__init__()
        # If address is given to instance, create ID from it
        self.address = address
        if address:
            self.docid = support.create_house_id(address)
        else:
            self.docid = None

        self.url = url

        # Format date properly; if not passed, set it to today
        if added_date:
            self.added_date = datetime.strptime(added_date, '%m/%d/%Y').date()
        else:
            self.added_date = datetime.now().date()

        # Add type to dictionary
        self['type'] = self.doctype

    def resolve_address_id(self):
        """Update address and ID as instance attributes.

        Checks if given address (at instance creation) matches what was
        scraped from the URL (if given). Also creates a unique ID for
        the address.
        """
        scraped_address = support.clean_address(self['main']['address'])
        scraped_addr_id = support.create_house_id(scraped_address)
        if self.docid:
            # address was provided to instance
            addr_ids_match = self.docid == scraped_addr_id
            if addr_ids_match:
                pass  # great!
            else:
                warnings.warn('address of House instance does not match \
                address from scraped URL. Keeping docid from instantiation.')
        else:
            # instance does not have addr or ID, fill them from scraped data
            self.address = scraped_address
            self.docid = scraped_addr_id

    def scrape(self, webdriver):
        """Fetch listing data from RealScout."""
        try:
            soup = scrape2.get_soup_for_url(self.url, webdriver)
        except AttributeError as e:  # url has not been set
            print(f'URL has not been set for this house. \n\t{e}')
            return
        listing_data = scrape2.scrape_soup(self, soup)
        self.update(listing_data)
        self.resolve_address_id()

    def upload(self):
        """Send JSON to database."""
        self.resolve_address_id()
        self['_id'] = self.docid
        try:
            database.push_one_to_db(self)
        except Exception as e:
            print(f'Upload failed, saving to disk.\n\t{e}')
            outfilename = support.create_filename_from_addr(self.address)
            outfilepath = path.join(Code.LISTINGS_DIR, outfilename)
            with open(outfilepath, 'w') as f:
                f.write(json.dumps(self, indent=4))
