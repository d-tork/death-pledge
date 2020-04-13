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
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
from django.utils.text import slugify
import logging
import subprocess

import Code
from Code import support, json_handling, classes
from Code.api_calls import keys, google_sheets

logger = logging.getLogger(__name__)


class ListingNotAvailable(Exception):
    pass


def sign_into_website(driver):
    """Open website and login to access restricted listings.

    Doesn't return anything; the browser is left open after signing in for
    another function to take over driving.

    Args:
        driver: Selenium WebDriver for navigating on the internet.
    
    """
    print('Opening browser and signing in...')
    driver.get(keys.website_url)
    username = driver.find_element_by_id('email_field')
    password = driver.find_element_by_id('user_password')

    username.send_keys(keys.website_email)
    password.send_keys(keys.website_pw)
    sleep(2)
    driver.find_element_by_name('commit').click()
    try:
        element = WebDriverWait(driver, 60).until(
            EC.title_contains('My Matches'))
        print('\tsigned in.')
    except TimeoutException:
        print('\tfailed to sign in.')


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
        close_driver = True
        options = Options()
        options.headless = quiet
        while True:
            try:
                driver = webdriver.Firefox(options=options, executable_path=Code.GECKODRIVER_PATH)
            except WebDriverException:
                options.headless = True  # override preference because it can't display browser
                continue
            break
        sign_into_website(driver)
    else:
        close_driver = False  # it's part of a context manager, no need to quit it

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
        if close_driver:
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
        attr_tup = tag.text.split(u':\xa0 ')
        attr_tup = [x.strip() for x in attr_tup]  # Strip whitespace from k and v
        attr_tup = [slugify(attr_tup[0]).replace('-', '_'), attr_tup[1]]
        yield attr_tup


def scrape_history_card(attrib_list):
    """Generate rows from the Listing History table.

    Yields: named tuple
    """
    row_items = []
    for i, tag in enumerate(attrib_list):
        val = tag.text.strip()
        row_items.append(val)
        if (i + 1) % 3 == 0:  # Third (last) item
            datestr = datetime.strptime(row_items[0], '%b %d, %Y').date()
            from_event, to_event = row_items[1], row_items[2]
            current_row = (str(datestr), f'{from_event} --> {to_event}')
            row_items = []
            yield current_row


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
                    for row in scrape_history_card(card_attrib_list):
                        data[card_title].update({row[0]: row[1]})
    return


def scrape_soup(house, soup):
    """Scrape all for a single BS4 soup object.

    Returns: dict
    """
    # Initialize dict with metadata
    scrape_data = house.setdefault('scrape_data', {})
    scrape_data['added_date'] = str(house.added_date)
    scrape_data['url'] = house.url
    scrape_data['scraped_time'] = str(datetime.now())
    scrape_data['scraped_source'] = 'RealScout'

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
    # Whole sub-dicts
    house['listing']['expenses_taxes'] = house.pop('expenses_taxes')
    house['listing']['listing_history'] = house.pop('listing_history')
    return house


def scrape_from_url_df(url_df, quiet=True):
    """Given an array of URLs, create house instances and scrape web data.

    Args:
        url_df (DataFrame): Two-series dataframe of URL and date added.
        quiet (bool): Whether to hide (True) or show (False) web browser as it
            scrapes.

    Returns:
        list: Array of house instances.

    """
    options = Options()
    options.headless = quiet

    house_list = []
    docid_list = []  # for checking for duplicate house instances

    with webdriver.Firefox(options=options, executable_path=Code.GECKODRIVER_PATH) as wd:
        # Check geckodriver version (SO 50359334)
        output = subprocess.run(['geckodriver', '-V'], stdout=subprocess.PIPE, encoding='utf-8')
        version = output.stdout.splitlines()[0]
        print(f'Geckodriver version: {version}\n')

        # On to the scraping
        sign_into_website(wd)
        print('Navigating to URLs...\n')
        for row in url_df.itertuples():
            random.seed()
            wait_time = random.random() * 5

            # Check if URL is valid
            result_code = support.check_status_of_website(row.url)
            if result_code != 200:
                print('URL did not return valid response code.')
                continue

            # Create house instance
            current_house = classes.Home(url=row.url, added_date=row.date_added)
            current_house.scrape(driver=wd)
            if current_house.docid not in docid_list:
                # Don't add instance if docid (based on address) already exists
                docid_list.append(current_house.docid)
                house_list.append(current_house)

            print('Waiting {:.1f} seconds...'.format(wait_time))
            sleep(wait_time)
            gc.collect()
    return house_list


if __name__ == '__main__':
    sample_url_list = [keys.sample_url, keys.sample_url2, keys.sample_url3]
    #sample_house = classes.Home(url=sample_url_list[0])
    sample_house = classes.Home(url='https://daniellebiegner.realscout.com/homesearch/listings/p-5825-piedmont-dr-alexandria-22310-brightmls-33')
    sample_house.scrape(quiet=False)
    sample_house.clean()
    print(json.dumps(sample_house['main'], indent=2))
    sample_house.upload('deathpledge_test')
