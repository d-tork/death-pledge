"""Scrape listing URLs for details that I would normally input myself.

This module returns no values; it is meant to accumulate a listing's
details in a dictionary, then write that dictionary to a JSON file
(or append the dict to the list of JSON dictionaries if the file already
exists).

"""
import random
import gc
from datetime import datetime
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import Firefox
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
from django.utils.text import slugify
import logging
import subprocess
from itertools import zip_longest

import deathpledge
from deathpledge import support, classes, database
from deathpledge.api_calls import keys, google_sheets

logger = logging.getLogger(__name__)


class ListingNotAvailable(Exception):
    pass


class HomesWithRawData(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_fetched_homes_to_list(self, rows):
        homes_fetched_from_raw_db = [home for home in bulk_fetch_from_raw_db(rows)]
        self.extend(homes_fetched_from_raw_db)


class SeleniumDriver(object):
    _options = Firefox.Options()
    geckodriver_path = deathpledge.GECKODRIVER_PATH

    def __init__(self, quiet=True, *args, **kwargs):
        self._webdriver = webdriver.Firefox()
        self._options.headless = quiet

    def __enter__(self):
        self._webdriver.__enter__(options=self._options, executable_path=self.geckodriver_path)

    def __exit__(self, type, value, traceback):
        try:
            self._webdriver.__exit(self, type, value, traceback)
        except:
            pass

    def get_geckodriver_version(self):
        """SO 50359334"""
        print(self.geckodriver_path)
        output = subprocess.run(
            [self.geckodriver_path, '-V'],
            stdout=subprocess.PIPE,
            encoding='utf-8'
        )
        version = output.stdout.splitlines()[0]
        print(f'Geckodriver version: {version}\n')

    def sign_into_website(self):
        """Open website and login to access restricted listings.

        Doesn't return anything; the browser is left open after signing in for
        another function to take over driving.

        Args:
            driver: Selenium WebDriver for navigating on the internet.

        """
        print('Opening browser and signing in...')
        self._webdriver.get(keys.website_url)
        self.enter_website_credentials(keys.website_email, keys.website_pw)
        try:
            self.wait_for_successful_signin()
        except TimeoutException as e:
            raise Exception('Failed to sign in.').with_traceback(e.__traceback__)

    def enter_website_credentials(self, email, password):
        email_field = self._webdriver.find_element_by_id('email_field')
        password_field = self._webdriver.find_element_by_id('user_password')

        email_field.send_keys(email)
        password_field.send_keys(password)
        sleep(2)
        self._webdriver.find_element_by_name('commit').click()

    def wait_for_successful_signin(self):
        element = WebDriverWait(self._webdriver, 60).until(
            EC.title_contains('My Matches'))
        print('\tsigned in.')


def scrape_from_url_df(urls, quiet=True):
    """Given an array of URLs, create house instances and scrape web data.

    Args:
        urls (DataFrame): Two-series dataframe of URL and date added.
        quiet (bool): Whether to hide (True) or show (False) web browser as it
            scrapes.

    Returns:
        list: Array of house instances.

    """
    home_list = HomesWithRawData()   # for passing on to caller
    docid_list = []                  # for checking for duplicate house instances

    # Fetch existing raw data for no-scrape listings, if not forced
    if urls.force_all:
        pass
    else:
        home_list.add_fetched_homes_to_list(urls.rows_not_to_scrape)

    with SeleniumDriver(quiet=quiet) as wd:
        wd.sign_into_website()

        print('Navigating to URLs...\n')
        for row in urls.rows_to_scrape.itertuples(index=False):
            random.seed()
            wait_time = random.random() * 5

            # Check if URL is valid
            result_code = support.check_status_of_website(row.url)
            if result_code != 200:
                print('URL did not return valid response code.')
                continue

            # Create house instance
            current_house = classes.Home(**row._asdict())  # unpacks the named tuple
            current_house.scrape(driver=wd, force=True)    # if it made it this far, it should be scraped
            if current_house.docid not in docid_list:
                # Don't add instance if docid (based on address) already exists
                docid_list.append(current_house.docid)
                home_list.append(current_house)

            if not current_house.skipped:
                # wait some time to be a courteous web scraper
                #print('Waiting {:.1f} seconds...'.format(wait_time))
                #sleep(wait_time)
                pass
            gc.collect()
    return home_list




def get_soup_for_url(url, driver=None, quiet=True):
    """Get BeautifulSoup object for a URL.
    
    Args:
        url (str): URL for listing.
        driver (optional): Selenium WebDriver; if not provided, this scrape
            is not part of bulk collection, thus a webdriver must be opened.
        quiet (bool, optional): True to hide browser, False to show it.

    Returns:
        bs4 soup object

    Raises:
        ValueError: If URL is invalid.
        ListingNotAvailable
        TimeoutException: If listing details don't appear within 10 sec after navigation.
    
    """
    print(f'URL: {url}')
    # Check if URL is valid before signing in, potentially saving the trouble
    result_code = support.check_status_of_website(url)
    if result_code != 200:
        raise ValueError('URL did not return valid response code.')

    if not driver:
        close_driver_reminder = True
        options = Options()
        options.headless = quiet
        driver = webdriver.Firefox(options=options, executable_path=deathpledge.GECKODRIVER_PATH)
        sign_into_website(driver)
    else:
        close_driver_reminder = False  # it's part of a context manager, no need to quit it

    try:
        driver.get(url)
        if 'Listing unavailable.' in driver.page_source:
            raise ListingNotAvailable("Bad URL or listing no longer exists.")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'listing-detail')))
        except TimeoutException:
            raise TimeoutException('Listing page did not load.')

        return BeautifulSoup(driver.page_source, 'html.parser')
    except Exception:
        # to ensure manually created driver is quit
        raise
    finally:
        if close_driver_reminder:
            driver.quit()


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
            }
    listing = {
        'badge': badge,
    }
    return main, listing


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


def grouper(iterable, n, fillvalue=None):
    """For iterating over a list in chunks of n size"""
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def get_cards(soup, data):
    """Parse all cards.

    Args:
        soup: BeautifulSoup object
        data (Home): instance of Home, dict to be updated

    Returns: dict

    """
    data['basic_info'] = data.setdefault('basic_info', {})
    # Get list of card tags
    cards = soup.find_all('div', attrs={'class': 'card'})

    # First card, no title (basic info)
    # except for MLS Number and Status, these are duplicates from further down the page
    tag_basic_info = cards[0]
    basic_info_list = tag_basic_info.find_all('div', class_='col-12')
    for field in basic_info_list:
        attr_tup = tuple(field.text.split(u':\xa0 '))
        attr_tup = (slugify(attr_tup[0]).replace('-', '_'), attr_tup[1])
        data['basic_info'].update([attr_tup])

    # All good cards
    for i, card in enumerate(cards):
        card_head = card.find('div', class_='card-header')
        if i == 0:  # Description paragraph
            data['listing']['description'] = card_head.text
        elif card_head:
            card_title = card_head.string
            if card_title:
                discard = ['which', 'open houses', 'questions']
                if any(x in card_title.lower() for x in discard):
                    continue
                card_title = slugify(card_title).replace('-', '_')

                # Create the key, in case names change or it's new
                data[card_title] = data.setdefault(card_title, {})
                card_attrib_list = card.find_all('div', class_='col-12')
                if card_attrib_list:
                    for field_attrib in scrape_normal_card(card_attrib_list):
                        data[card_title].update([field_attrib])
                else:  # the Listing History card
                    card_attrib_list = card.find_all('div', class_='col-4')
                    data[card_title] = scrape_history_card(card_attrib_list)
    return


def scrape_soup(house, soup):
    """Scrape all for a single BS4 soup object.

    Returns: dict
    """
    # Initialize dict with metadata
    scrape_data = house.setdefault('scrape_data', {})
    scrape_data['url'] = house.url
    scrape_data['scraped_time'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
    scrape_data['scraped_source'] = 'RealScout'
    house['added_date'] = house.added_date.strftime(deathpledge.TIMEFORMAT)

    # Scrape three sections
    house['main'], house['listing'] = get_main_box(soup)
    house['listing'].update(get_price_info(soup))
    get_cards(soup, house)

    # Reorganize sub-dicts
    single_items = [
        ('basic_info', 'tax_annual_amount'),
        ('basic_info', 'price_per_sqft'),
        ('basic_info', 'status'),
        ('basic_info', 'mls_number'),
    ]
    for subdict, key in single_items:
        house['listing'][key] = house[subdict].pop(key, None)
    del house['basic_info']
    # Whole sub-dicts
    house['listing']['expenses_taxes'] = house.pop('expenses_taxes')
    house['listing']['listing_history'] = house.pop('listing_history')
    return house


def bulk_fetch_from_raw_db(url_df):
    """Create Home instances from data already in raw."""
    responses = database.get_multiple_docs(doc_ids=list(url_df['docid']))
    for response in responses:
        raw_doc = response['doc']
        home = classes.Home(
            full_address=raw_doc['main'].get('full_address'),
            url=raw_doc['scrape_data'].get('url'),
            added_date=raw_doc.get('added_date'),
            docid=raw_doc.get('_id')
        )
        home.update(raw_doc)
        home.skipped = True
        yield home


if __name__ == '__main__':
    sample_url_list = [keys.sample_url, keys.sample_url2, keys.sample_url3]
    #sample_house = classes.Home(url=sample_url_list[0])
    sample_house = classes.Home(url='https://daniellebiegner.realscout.com/homesearch/listings/p-5825-piedmont-dr-alexandria-22310-brightmls-33')
    sample_house.scrape(quiet=False, force=True)
    sample_house.clean()
    print(json.dumps(sample_house['main'], indent=2))
    sample_house.upload('deathpledge_test')
