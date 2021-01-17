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
            ListingNotAvailable
            TimeoutException: If listing details don't appear within 10 sec after navigation.

        """
        self.logger.info(f'scraping URL: {url}')
        if not scrape.url_is_valid(url):
            raise ValueError()

        self.webdriver.get(url)
        if 'Listing unavailable.' in self.webdriver.page_source:  # TODO: remove or replace with homescout version
            raise classes.ListingNotAvailable("Bad URL or listing no longer exists.")

        try:
            WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located((By.ID, 'listing-detail')))  # TODO: modify for homescout
        except TimeoutException:
            raise TimeoutException('Listing page did not load.')

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

    def scrape_soup(self):
        """Scrape all for a single BS4 self object.

        TODO: refactor for homescout listing page

        Returns: dict
        """
        # Initialize dict with metadata
        self.data['scraped_time'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
        self.data['scraped_source'] = 'Homescout'
        self.logger.debug('Added scraping operation metadata')

        # Process three sections
        self.data.update(self._get_main_box())
        self.data.update(self._get_price_info())
        self.data.update(self._get_cards())

    def _get_main_box(self) -> dict:
        """Add box details to home instance."""
        self.logger.debug('Getting main box details')
        result = self.find_all('div', attrs={'class': 'col-8 col-sm-8 col-md-7'})
        main_box = result[0]

        # Extract strings from tags
        badge = str(main_box.a.string)
        address = str(main_box.h1.string)
        citystate = str(main_box.h2.string)
        vitals = main_box.h5.text.split(' |\xa0')

        main_data = {
            'address': address,
            'city_state': citystate,
            'full_address': ' '.join([address, citystate]),
            'beds': vitals[0],
            'baths': vitals[1],
            'sqft': vitals[2],
            'badge': badge,
        }
        return main_data

    def _get_price_info(self) -> dict:
        """Add price info details to home instance."""
        self.logger.debug('Getting price and status info')
        info_data = {}
        result = self.find_all('div', attrs={'class': 'col-4 col-sm-4 col-md-5 text-right'})
        box = result[0]
        price = box.h2.text
        info_data['list_price'] = price

        try:
            badge = box.p
            if 'sold' in badge.text.lower():
                date_sold = badge.text.split(': ')[-1]
                date_sold = str(datetime.strptime(date_sold, '%m/%d/%Y'))
                list_price = box.small.text.split()[-1]
                info_data.update({
                    'sold': date_sold,
                    'sale_price': price,
                    'list_price': list_price,
                })
        except AttributeError:
            logger.debug(f'Error while getting price info, probably Off Market or In Contract.')
        return info_data

    def _get_cards(self) -> dict:
        """Parse all cards."""
        self.logger.debug('Processing cards')
        card_data = {}
        cards = self.find_all('div', attrs={'class': 'card'})

        # First card, no title (basic info)
        # except for MLS Number and Status, these are duplicates from further down the page
        basic_info_card = cards[0]
        basic_info_data = self._get_fields_in_basic_info_card(basic_info_card)
        card_data.update(basic_info_data)

        # All good cards
        self.logger.debug('Processing all cards')
        for i, card in enumerate(cards):
            card_head = card.find('div', class_='card-header')
            if i == 0:
                self.logger.debug('Adding description pargraph')
                card_data['description'] = card_head.text
            elif card_head:
                card_title = card_head.string
                if card_title:
                    discard = ['which', 'open houses', 'questions']
                    if any(x in card_title.lower() for x in discard):
                        continue

                    # Create the key, in case names change or it's new
                    card_attrib_list = card.find_all('div', class_='col-12')
                    if card_attrib_list:
                        normal_card_data = get_normal_card_data(card_attrib_list)
                        card_data.update(normal_card_data)
                    else:
                        self.logger.debug('Processing the listing history card')
                        card_attrib_list = card.find_all('div', class_='col-4')
                        card_data['listing_history'] = self._scrape_history_card(card_attrib_list)
        return card_data

    @staticmethod
    def _get_fields_in_basic_info_card(card) -> dict:
        """Extract fields and values from basic info card."""
        basic_info_list = card.find_all('div', class_='col-12')
        basic_info_data = {}
        for field in basic_info_list:
            name, value = tuple(field.text.split(u':\xa0 '))
            name = (slugify(name).replace('-', '_'))
            basic_info_data[name] = value
        return basic_info_data

    @staticmethod
    def _scrape_history_card(attrib_list: list) -> list:
        """Create array of listing history objects."""
        history_array = []
        for row in grouper(attrib_list, 3):
            key_list = ['date', 'from', 'to']
            val_list = [tag.text.strip() for tag in row]

            obj = dict(zip(key_list, val_list))
            obj['date'] = str(datetime.strptime(obj.get('date'), '%b %d, %Y').date())

            # Parse currencies
            for k, v in obj.items():
                try:
                    obj[k] = float(v.replace(',', '').replace('$', ''))
                except ValueError:
                    continue
            history_array.append(obj)
        return history_array


def get_normal_card_data(attrib_list: list) -> dict:
    """Extract fields and values from a normal card."""
    card_data = {}
    for tag in attrib_list:
        attribute_pair = tuple(tag.text.split(u':'))
        attribute_pair = [x.strip() for x in attribute_pair]  # Strip whitespace from both
        name, value = attribute_pair
        name = slugify(attribute_pair[0]).replace('-', '_')
        card_data[name] = value
    return card_data


def grouper(iterable, n, fillvalue=None):
    """For iterating over a list in chunks of n size"""
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)
