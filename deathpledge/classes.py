"""Class definitions for death-pledge."""

from datetime import datetime
from os import path
import json
import logging

import deathpledge
from deathpledge import database, support, cleaning, enrich


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

    def __init__(self, url=None, added_date=None, docid=None, **throwaway):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        super().__init__()
        self.docid = docid
        self.url = url
        self.added_date = self._set_added_date(added_date)

        # Leave this switch to be flipped elsewhere
        self.skip_web_scrape = False
        # Add type to dictionary for database record
        self['doctype'] = self.doctype

    def __str__(self):
        return json.dumps(self, indent=2)

    @staticmethod
    def _set_added_date(passed_date):
        """Format date properly; if not passed or fetched, set it to today"""
        if passed_date:
            added_date = support.coerce_date_string_to_date(passed_date)
        else:
            added_date = datetime.now()
        return added_date

    def fetch(self, db_name, db_client):
        """Retrieve existing data from database."""
        if self.docid:
            try:
                existing_doc = database.get_single_doc(
                    doc_id=self.docid, db_name=db_name, client=db_client
                )
            except KeyError:
                self.logger.info('Document was not fetched.')
            else:
                self.update(existing_doc)
        return

    def scrape(self, website_object):
        """Fetch listing data from RealScout."""
        try:
            soup = website_object.get_soup_for_url(self.url)
        except:
            self.logger.exception(f'Failed to get soup for {self.url}')
            raise
        soup.scrape_soup()
        self.update(soup.data)
        self._add_class_attributes_as_dict_keys()

    def _add_class_attributes_as_dict_keys(self):
        """Add attributes to the data dictionary for this instance."""
        self['url'] = self.url
        self['added_date'] = self.added_date.strftime(deathpledge.TIMEFORMAT)

    def clean(self):
        """Parse and clean all string values meant to be numeric.

        Also drops unneeded/duplicate fields. Set up to catch exceptions
        so cleaning can happen or fail to happen without disrupting the flow.
        For example, a home fetched from the database would not need cleaning.
        """
        self.logger.info(f'Cleaning {self.docid}')
        cleaning_funcs = [
            cleaning.split_comma_delimited_fields,
            cleaning.convert_numbers,
            cleaning.split_fee_frequency,
            cleaning.parse_address,
            cleaning.parse_homescout_date,
        ]
        for fn in cleaning_funcs:
            try:
                fn(self)
            except (AttributeError, ValueError, KeyError) as e:
                self.logger.warning(f"Cleaning step '{fn}' failed: {e}")
                continue

    def enrich(self):
        """Add additional values from external sources."""
        try:
            enrich.add_bing_maps_data(self)
        except:
            self.logger.exception('Bing enriching failed.')
        enrich.add_tether(self)

    def get_geocoords(self):
        try:
            geocoords = self.get('geocoords')
        except KeyError:
            enrich.add_coords(self, force=True)
            geocoords = self.get('geocoords')
        return geocoords

    def upload(self, db_name, db_client):
        """Send JSON to database."""
        try:
            database.push_one_to_db(self, db_name=db_name, client=db_client)
        except Exception:
            self.logger.error('Upload failed, saving to disk.', exc_info=True)
            self.save_local()
        return

    def save_local(self, filename=None):
        if not filename:
            filename = support.create_filename_from_addr(self.get('full_address'))
        outfilepath = path.join(deathpledge.LISTINGS_DIR, filename)
        with open(outfilepath, 'w') as f:
            f.write(json.dumps(self, indent=4))


class ListingNotAvailable(Exception):
    pass


class WebDataSource(object):
    """Website for scraping and related configuration.

    Args:
        webdriver: Selenium WebDriver for navigating in a browser.

    """

    def __init__(self, webdriver):
        self.webdriver = webdriver

    def get_soup_for_url(self):
        raise NotImplementedError('Subclass must implement abstract method')
