"""Class definitions for death-pledge."""

from datetime import datetime
from os import path
import json
import warnings
import logging
import pytz

import deathpledge
from deathpledge import scrape2, database, support, cleaning, enrich

logger = logging.getLogger(__name__)


class Home(dict):
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

    Process
    =======
    1. Instantiate
    2. Scrape
    3. Write raw to db (all sub-dicts)
    4. Clean
    5. Enrich
    6. Split and score
    7. Write processed *data* to db (excluding listing sub-dict)

    Attributes:
        doctype (str): type of document to store

    Args:
        full_address (str): property street address in the form
            123 NORTH MAPLE DR 456 ALEXANDRIA VA 22302
        url (str): url to be scraped for data
        added_date (str): date house was first considered, in the form 1/1/2020
        docid (str): hash of address

    """
    doctype = 'home'

    def __init__(self, full_address=None, url=None, added_date=None, docid=None, **kwargs):
        super().__init__()
        self.docid = docid
        # If address is given to instance, make sure it's cleaned
        if full_address:
            self.full_address = support.clean_address(full_address)
            if not self.docid:
                # If docid not given, generate it now
                self.docid = support.create_house_id(self.full_address)
        else:
            self.full_address = None

        self.url = url

        # Add type to dictionary
        self['doctype'] = self.doctype
        # Whether to skip the web scraping
        self.skip_web_scrape = False

        # Format date properly; if not passed or fetched, set it to today
        if added_date:
            self.added_date = support.coerce_date_string_to_date(added_date)
        else:
            self.added_date = datetime.now()

    def __str__(self):
        return json.dumps(self, indent=2)

    def resolve_address_and_id(self):
        """Update address and ID as instance attributes.

        Checks if given address (at instance creation) matches what was
        scraped from the URL (if given). Also creates a unique ID for
        the address.
        """
        scraped_address = support.clean_address(self['full_address'])
        scraped_addr_id = support.create_house_id(scraped_address)
        if self.docid:
            # address was provided to instance
            addr_ids_match = self.docid == scraped_addr_id
            if addr_ids_match:
                pass  # great!
            else:
                warnings.warn('address of Home instance does not match \
                address from scraped URL. Keeping docid from instantiation.')
        else:
            # instance does not have addr or ID, fill them from scraped data
            self.full_address = scraped_address
            self.docid = scraped_addr_id
        self['_id'] = self.docid

    def in_db(self):
        """Check if home in database."""
        return database.check_for_doc(deathpledge.DATABASE_NAME, self.docid)

    def fetch(self):
        """Retrieve existing data from database."""
        if not self.docid:
            self.resolve_address_and_id()
        try:
            existing_doc = database.get_single_doc(deathpledge.RAW_DATABASE_NAME, self.docid)
        except KeyError:
            logger.info('Document was not fetched.')
            return
        self.update(existing_doc)

    def scrape(self, website_object):
        """Fetch listing data from RealScout."""
        try:
            soup = website_object.get_soup_for_url(self.url)
        except Exception as e:
            logger.exception(f'Failed to get soup for {self.url}')
            return
        listing_data = scrape2.scrape_soup(self, soup)
        self.update(listing_data)
        self.resolve_address_and_id()

    def clean(self):
        """Parse and clean all string values meant to be numeric.

        Also drops unneeded/duplicate fields. Set up to catch exceptions
        so cleaning can happen or fail to happen without disrupting the flow.
        For example, a home fetched from the database would not need cleaning.
        """
        cleaning_funcs = [
            cleaning.split_comma_delimited_fields,
            cleaning.convert_numbers,
            # cleaning.convert_dates,
            cleaning.remove_dupe_fields,
            cleaning.parse_address,
        ]
        for fn in cleaning_funcs:
            try:
                fn(self)
            except (AttributeError, ValueError) as e:
                logger.exception(f'Cleaning step failed: {e}')
                continue

    def enrich(self):
        """Add additional values from external sources."""
        enrich.add_coords(self, force=True)
        enrich.add_bing_commute(self)

    def save_local(self, filename=None):
        if not filename:
            filename = support.create_filename_from_addr(self.full_address)
        outfilepath = path.join(deathpledge.LISTINGS_DIR, filename)
        with open(outfilepath, 'w') as f:
            f.write(json.dumps(self, indent=4))

    def upload(self, db_name):
        """Send JSON to database."""
        try:
            self.resolve_address_and_id()
        except KeyError:
            print("Could not resolve address and doc id.",
                  "Are you sure you've scraped the listing?",
                  "\n\tSaving to disk.")
            self.update(vars(self))
            outfilename = f'Unknown_home-{datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}.json'
            self.save_local(filename=outfilename)
            return
        self['_id'] = self.docid
        try:
            database.push_one_to_db(self, db_name=db_name)
        except Exception as e:
            print(f'Upload failed, saving to disk.\n\t{e}')
            self.save_local()
        return

