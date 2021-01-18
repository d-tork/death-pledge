"""
Module for scraping from homescout

"""
import logging
from datetime import datetime
from time import sleep
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from django.utils.text import slugify
from itertools import zip_longest
from collections import namedtuple
from urllib.parse import urlparse

import deathpledge
from deathpledge import scrape2 as scrape
from deathpledge import classes

logger = logging.getLogger(__name__)


class HomeScoutWebsite(classes.WebDataSource):
    """Container for Homescout website and access methods for scraping the self."""

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self._config = deathpledge.keys['Homescout']
        super().__init__(*args, **kwargs)
        self.signed_in = False

    def sign_into_website(self):
        """Open website and login to access restricted listings."""
        self.logger.info('Opening browser and signing in')
        self.webdriver.get(self._config['sign_in_url'])
        self._enter_website_credentials()
        try:
            self._wait_for_successful_signin()
        except TimeoutException as e:
            raise Exception('Failed to sign in.').with_traceback(e.__traceback__)
        else:
            self.signed_in = True

    def _enter_website_credentials(self):
        login_link = self.webdriver.find_elements_by_class_name('action-link')[1]
        login_link.click()

        inputs = self.webdriver.find_elements_by_class_name('login-textbox')
        email_field, password_field = inputs[6:8]

        email_field.send_keys(self._config['email'])
        password_field.send_keys(self._config['password'])
        login_button = self.webdriver.find_element(By.CLASS_NAME, 'login-button')
        login_button.click()

    def _wait_for_successful_signin(self):
        mystuff = self.webdriver.find_element_by_class_name('mystuff-link')
        WebDriverWait(self.webdriver, 15).until(EC.visibility_of(mystuff))
        self.logger.info('signed in')

    def collect_listings(self, max_pages: int) -> list:
        self.webdriver.get(self._config['results_url'])
        sleep(2)
        listing_pages = []
        for page in range(1, max_pages):
            results_page_soup = HomeScoutList(self.webdriver.page_source, 'html.parser')
            listing_pages.append(results_page_soup)
            WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'mcl-paging-next'))
            )
            paging_buttons = self._get_paging_buttons()
            next_button = paging_buttons[1]
            next_button.click()
            sleep(2)
        return listing_pages

    def _get_paging_buttons(self):
        return self.webdriver.find_elements_by_class_name('mcl-paging-next')

    def get_soup_for_url(self, url):
        """Get BeautifulSoup object for a URL.

        Args:
            url (str): URL for listing.

        Returns:
            HomeScoutSoup object

        Raises:
            ValueError: If URL is invalid.
            TimeoutException: If listing details don't appear within 10 sec after navigation.

        """
        self.logger.info(f'scraping URL: {url}')
        if not scrape.url_is_valid(url):
            raise ValueError()

        self.webdriver.get(url)
        try:
            WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'agent-header')))
        except TimeoutException:
            raise TimeoutException('Listing did not load.')

        return HomeScoutSoup(self.webdriver.page_source, 'html.parser')


class HomeScoutList(BeautifulSoup):
    """Container for Homescout search results in list format.

    Needs method to parse all cards on each page. Should collect address, price, status, and url.

    """
    Card = namedtuple('Card', 'price status address city_state_zip url mls')
    base_url = 'https://homescout.homescouting.com'

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        super().__init__(*args, **kwargs)

    def scrape_page(self) -> list:
        gallery_items = self.find_all('div', attrs={'class': 'gallery-page-item'})
        parsed_cards = []
        for card in gallery_items:
            card_data = self._parse_gallery_card(card)
            parsed_cards.append(card_data)
        return parsed_cards

    def _parse_gallery_card(self, card) -> Card:
        """Parse BS4 element tag for a card in the gallery."""
        price, status = self._get_price_status_from_card(card)
        address, city_state_zip = self._get_address_from_card(card)
        url = self._get_url_from_card(card)
        mls = self._get_mls_from_url(url)
        return self.Card(price, status, address, city_state_zip, url, mls)

    @staticmethod
    def _get_price_status_from_card(card) -> tuple:
        listing_price_div = card.find_all('div', attrs={'class': 'gallery-listing-price'})
        price, status = [str(x.text) for x in listing_price_div]
        return price, status

    @staticmethod
    def _get_address_from_card(card) -> tuple:
        address_div = card.find('div', attrs={'class': 'gallery-card-address'})
        address = str(address_div.contents[1])
        city_state_zip = str(address_div.contents[3].text)
        return address, city_state_zip

    def _get_url_from_card(self, card):
        url_suffix = card.find('a', attrs={'class': 'photoLink'}).get('href')
        return ''.join([self.base_url, url_suffix])

    @staticmethod
    def _get_mls_from_url(url):
        parsed = urlparse(url)
        query = parsed.query.split('&')
        mls_query = [x for x in query if x.startswith('MLSListingID')][0]
        mls = mls_query[mls_query.find('=') + 1:]
        return mls


class HomeScoutSoup(BeautifulSoup):
    """Container for Homescout html soup.

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
        self.data['scraped_source'] = 'Homescout'
        self.logger.debug('Added scraping operation metadata')

        # Process three sections
        self.data.update(self._get_main_box())
        self.data.update(self._get_quick_look())
        self.data.update(self._get_estimated_value())
        self.data.update(self._get_advanced())

    def _get_div_string(self, classname):
        return str(self.find('div', attrs={'class': classname}))

    def _get_address(self):
        address = self._get_div_string('detail-addr')
        city_state_zip = self._get_div_string('detail-addr2')
        return address, city_state_zip

    def _get_price_and_status(self):
        details_tag = self.find('div', attrs={'class': 'detail-listing-price'})
        price = details_tag.contents[5]
        status = details_tag.contents[11]
        return price, status

    def _get_vitals(self):
        vitals_tag = self.find_all('div', attrs={'class': 'detail-info1'})
        Vitals = namedtuple('Vitals', 'beds baths sqft')
        vitals = Vitals(
            beds=self._parse_vitals_text(vitals_tag[0].text),
            baths=self._parse_vitals_text(vitals_tag[1].text),
            sqft=self._parse_vitals_text(vitals_tag[2].text)
        )
        return vitals

    @staticmethod
    def _parse_vitals_text(s):
        return int(s.strip().split()[0])

    def _get_main_box(self) -> dict:
        """Add box details to home instance."""
        self.logger.debug('Getting main box details')
        price, status = self.get_price_and_status()
        address, citystate = self._get_address()
        vitals = self._get_vitals()

        main_data = {
            'address': address,
            'city_state': citystate,
            'full_address': ' '.join([address, citystate]),
            'beds': vitals.beds,
            'baths': vitals.baths,
            'sqft': vitals.sqft,
            'badge': status,
            'list_price': price
        }
        return main_data

    def _get_quick_look(self) -> dict:
        """Add price info details to home instance."""
        self.logger.debug('Getting quick look')
        quick_data = {}
        quicklook = self.find('div', attrs={'class': 'detail-left quick-look'})
        attributes = quicklook.find_all('div', attrs={'class': 'attribute'})
        for attrib in attributes:
            attrib_name, attrib_value = attrib.text.split(':  ')
            attrib_name = self._slugify(attrib_name)
            quick_data[attrib_name] = attrib_value
        return quick_data

    def _get_estimated_value(self) -> dict:
        price_box = self.find_all('div', attrs={'class': 'price-box'})[0].text
        return dict(estimated_value=str(price_box))

    @staticmethod
    def _slugify(s):
        return slugify(s).replace('-', '_')

    def _get_advanced(self) -> dict:
        """Parse advanced details."""
        self.logger.debug('Scraping details')
        advanced_data = {}
        feature_groups = self.find('div', attrs={'class': 'detail-feature-groups'})
        features = feature_groups.find_all('div', attrs={'class': 'feature-display'})
        for feature in features:
            feature_name = self._slugify(feature.find('span', attrs={'class': 'feature-name'}).text)
            feature_val = feature.find('span', attrs={'class': 'feature-value'}).text
            advanced_data[feature_name] = feature_val
        return advanced_data
