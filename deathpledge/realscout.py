"""
Module for scraping from realscout

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

import deathpledge
from deathpledge import scrape2 as scrape
from deathpledge import classes

logger = logging.getLogger(__name__)


class RealScoutWebsite(classes.WebDataSource):
    """Container for Realscout website and access methods for scraping the self."""

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self._config = deathpledge.keys['Realscout']
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
        email_field = self.webdriver.find_element_by_id('email_field')
        password_field = self.webdriver.find_element_by_id('user_password')

        email_field.send_keys(self._config['email'])
        password_field.send_keys(self._config['password'])
        sleep(2)
        self.webdriver.find_element_by_name('commit').click()

    def _wait_for_successful_signin(self):
        element = WebDriverWait(self.webdriver, 60).until(
            EC.title_contains('My Matches'))
        self.logger.info('signed in')

    def get_soup_for_url(self, url):
        """Get BeautifulSoup object for a URL.

        Args:
            url (str): URL for listing.

        Returns:
            RealScoutSoup object

        Raises:
            ValueError: If URL is invalid.
            ListingNotAvailable
            TimeoutException: If listing details don't appear within 10 sec after navigation.

        """
        self.logger.info(f'scraping URL: {url}')
        if not scrape.url_is_valid(url):
            raise ValueError()

        self.webdriver.get(url)
        if 'Listing unavailable.' in self.webdriver.page_source:
            raise classes.ListingNotAvailable("Bad URL or listing no longer exists.")

        try:
            WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located((By.ID, 'listing-detail')))
        except TimeoutException:
            raise TimeoutException('Listing page did not load.')

        return RealScoutSoup(self.webdriver.page_source, 'html.parser')


class RealScoutSoup(BeautifulSoup):
    """Container for Realscout html soup.

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

        Returns: dict
        """
        # Initialize dict with metadata
        self.data['scraped_time'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
        self.data['scraped_source'] = 'RealScout'
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

