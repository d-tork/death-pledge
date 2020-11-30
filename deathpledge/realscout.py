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

logger = logging.getLogger(__name__)


class ListingNotAvailable(Exception):
    pass


class WebDataSource(object):
    """Website for scraping and related configuration.

    Args:
        webdriver: Selenium WebDriver for navigating in a browser.

    """
    def __init__(self, webdriver):
        self._config = deathpledge.keys['Realscout']
        self.webdriver = webdriver

    def get_soup_for_url(self):
        raise NotImplementedError('Subclass must implement abstract method')


class RealScoutWebsite(WebDataSource):

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        super().__init__(*args, **kwargs)

    def sign_into_website(self):
        """Open website and login to access restricted listings."""
        self.logger.info('Opening browser and signing in')
        self.webdriver.get(self._config['sign_in_url'])
        self._enter_website_credentials()
        try:
            self._wait_for_successful_signin()
        except TimeoutException as e:
            raise Exception('Failed to sign in.').with_traceback(e.__traceback__)

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
        self.logger.info('signed in.')

    def get_soup_for_url(self, url):
        """Get BeautifulSoup object for a URL.

        Args:
            url (str): URL for listing.

        Returns:
            bs4 soup object

        Raises:
            ValueError: If URL is invalid.
            ListingNotAvailable
            TimeoutException: If listing details don't appear within 10 sec after navigation.

        """
        print(f'URL: {url}')
        if not scrape.url_is_valid(url):
            raise ValueError()

        self.webdriver.get(url)
        if 'Listing unavailable.' in self.webdriver.page_source:
            raise ListingNotAvailable("Bad URL or listing no longer exists.")

        try:
            WebDriverWait(self.webdriver, 10).until(
                EC.presence_of_element_located((By.ID, 'listing-detail')))
        except TimeoutException:
            raise TimeoutException('Listing page did not load.')

        return BeautifulSoup(self.webdriver.page_source, 'html.parser')


def get_main_box(soup):
    """Add box details to home instance.

    Args:
        soup: bs4 soup object.

    """
    # Get tags
    result = soup.find_all('div', attrs={'class': 'col-8 col-sm-8 col-md-7'})
    main_box = result[0]

    # Extract strings from tags
    badge = str(main_box.a.string)
    address = str(main_box.h1.string)
    citystate = str(main_box.h2.string)
    vitals = main_box.h5.text.split(' |\xa0')

    # Add to dictionary
    main = {
        'address': address,
        'city_state': citystate,
        'full_address': ' '.join([address, citystate]),
        'beds': vitals[0],
        'baths': vitals[1],
        'sqft': vitals[2],
        'badge': badge,
    }
    return main


def get_price_info(soup):
    """Add price info details to home instance."""
    info = {}
    # Get tags
    result = soup.find_all('div', attrs={'class': 'col-4 col-sm-4 col-md-5 text-right'})
    box = result[0]
    price = box.h2.text
    info['list_price'] = price

    try:
        badge = box.p
        if 'sold' in badge.text.lower():
            date_sold = badge.text.split(': ')[-1]
            date_sold = str(datetime.strptime(date_sold, '%m/%d/%Y'))
            list_price = box.small.text.split()[-1]
            info.update({
                'sold': date_sold,
                'sale_price': price,
                'list_price': list_price,
            })
    except AttributeError as e:
        logger.info(f'Error while getting price info: {e}, probably Off Market.')
    return info


def scrape_normal_card(attrib_list):
    """Generate field, attribute tuples from normal cards."""
    for tag in attrib_list:
        attr_tup = tag.text.split(u':')
        attr_tup = [x.strip() for x in attr_tup]  # Strip whitespace from k and v
        attr_tup = [slugify(attr_tup[0]).replace('-', '_'), attr_tup[1]]
        yield attr_tup


def grouper(iterable, n, fillvalue=None):
    """For iterating over a list in chunks of n size"""
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def scrape_history_card(attrib_list):
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


def get_cards(soup, data):
    """Parse all cards.

    Args:
        soup: BeautifulSoup object
        data (Home): instance of Home, dict to be updated

    Returns: dict

    """
    # Get list of card tags
    cards = soup.find_all('div', attrs={'class': 'card'})

    # First card, no title (basic info)
    # except for MLS Number and Status, these are duplicates from further down the page
    tag_basic_info = cards[0]
    basic_info_list = tag_basic_info.find_all('div', class_='col-12')
    for field in basic_info_list:
        attr_tup = tuple(field.text.split(u':\xa0 '))
        attr_tup = (slugify(attr_tup[0]).replace('-', '_'), attr_tup[1])
        data.update([attr_tup])

    # All good cards
    for i, card in enumerate(cards):
        card_head = card.find('div', class_='card-header')
        if i == 0:  # Description paragraph
            data['description'] = card_head.text
        elif card_head:
            card_title = card_head.string
            if card_title:
                discard = ['which', 'open houses', 'questions']
                if any(x in card_title.lower() for x in discard):
                    continue
                card_title = slugify(card_title).replace('-', '_')

                # Create the key, in case names change or it's new
                card_attrib_list = card.find_all('div', class_='col-12')
                if card_attrib_list:
                    for field_attrib in scrape_normal_card(card_attrib_list):
                        data.update([field_attrib])
                else:  # the Listing History card
                    card_attrib_list = card.find_all('div', class_='col-4')
                    data['listing_history'] = scrape_history_card(card_attrib_list)
    return


def scrape_soup(house, soup):
    """Scrape all for a single BS4 soup object.

    Returns: dict
    """
    # Initialize dict with metadata
    house['url'] = house.url
    house['scraped_time'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
    house['scraped_source'] = 'RealScout'
    house['added_date'] = house.added_date.strftime(deathpledge.TIMEFORMAT)

    # Scrape three sections
    house.update(get_main_box(soup))
    house.update(get_price_info(soup))
    get_cards(soup, house)
    return house
