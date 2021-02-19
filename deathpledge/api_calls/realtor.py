"""
Module for scraping from realtor.com

"""
import logging
from datetime import datetime
from time import sleep
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

import deathpledge
from deathpledge import scrape2 as scrape
from deathpledge import classes

logger = logging.getLogger(__name__)


class RealtorWebsite(classes.WebDataSource):
    """Container for Realtor.com website and access methods for scraping the self."""

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        super().__init__(*args, **kwargs)

    def collect_listings(self, max_pages: int) -> list:
        raise NotImplementedError()

    def get_soup_for_url(self, url):
        """Get BeautifulSoup object for a URL.

        Args:
            url (str): URL for listing.

        Returns:
            RealtorSoup object

        Raises:
            ValueError: If URL is invalid.

        """
        self.logger.info(f'scraping URL: {url}')
        if not scrape.url_is_valid(url):
            raise ValueError()

        self.webdriver.get(url)
        return RealtorSoup(self.webdriver.page_source, 'html.parser')


class RealtorSoup(BeautifulSoup):
    """Container for Realtor.com html soup.

    Attributes:
        data (dict): Fields and values processed from scraped listing. To be
            added to the Home() instance.

    """

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        super().__init__(*args, **kwargs)
        self.data = {}

    def scrape_soup(self) -> dict:
        """Scrape all for a single BS4 self object."""
        # Initialize dict with metadata
        self.data['scraped_time'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
        self.data['scraped_source'] = 'Realtor.com'
        self.logger.debug('Added scraping operation metadata')
        raise NotImplementedError()
