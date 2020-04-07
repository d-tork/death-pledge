"""Class definitions for death-pledge."""

from datetime import datetime
from os import path
import json

import Code
from Code import scrape2, database, support


class House(dict):
    def __init__(self, url=None, added_date=None):
        super().__init__()
        if url:
            self.url = url
        if added_date:
            self.added_date = datetime.strptime(added_date, '%m/%d/%Y').date()
        else:
            self.added_date = datetime.now().date()

    def scrape(self, webdriver):
        """Fetch listing data from RealScout."""
        try:
            soup = scrape2.get_soup_for_url(self.url, webdriver)
        except AttributeError as e:  # url has not been set
            print(f'URL has not been set for this house. \n\t{e}')
        listing_data = scrape2.scrape_soup(self, soup)
        self.update(listing_data)

    def upload(self):
        """Send JSON to database."""
        try:
            database.push_to_db(self)
        except Exception as e:
            print(f'Upload failed, saving to disk.\n\t{e}')
            outfilename = support.create_filename_from_dict(self)
            outfilepath = path.join(Code.LISTINGS_DIR, outfilename)
            with open(outfilepath, 'w') as f:
                f.write(json.dumps(self, indent=4))
