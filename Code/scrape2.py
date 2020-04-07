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
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json

import Code
from Code import support, json_handling
from Code.api_calls import keys, google_sheets


class ListingNotAvailable(Exception):
    pass


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
        try:
            soup = get_soup_for_url(self.url, webdriver)
        except TimeoutException as e:
            print(f'\t{e}')
        except AttributeError as e:  # url has not been set
            print(f'URL has not been set for this house. \n\t{e}')
        listing_data = scrape_soup(self, soup)
        self.update(listing_data)


def sign_into_website(driver):
    """Open website and login to access restricted listings.

    Doesn't return anything; the browser is left open after signing in for
    another function to take over driving.

    Args:
        driver: Selenium WebDriver for navigating on the internet.
    
    """
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


def get_soup_for_url(url, driver):
    """Get BeautifulSoup object for a URL.
    
    Args:
        url (str): URL for listing.
        driver: Selenium WebDriver

    Returns:
        bs4 soup object

    Raises:
        TimeoutException: If listing details don't appear within 10 sec after navigation.
    
    """
    url_suffix = url.rfind('/') + 3
    print('URL: {}'.format(url[url_suffix:]))
    driver.get(url)

    if 'Listing unavailable.' in driver.page_source:
        raise ListingNotAvailable("Bad URL or listing no longer exists.")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'listing-detail'))
        )
    except TimeoutException:
        raise TimeoutException('Listing page did not load.')

    return BeautifulSoup(driver.page_source, 'html.parser')


def get_main_box(soup):
    """Add box details to listing dictionary.

    Args: 
        soup: bs4 soup object.

    """
    # Get tags
    result = soup.find_all('div', attrs={'class': 'col-8 col-sm-8 col-md-7'})
    main_box = result[0]

    # Extract strings from tags
    badge = main_box.a.string
    address = main_box.h1.string
    citystate = main_box.h2.string
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
    """Add price info details to listing dictionary."""
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
        print(f'Error while getting price info: {e}')
        # Most likely "Off Market"
    return info


def scrape_normal_card(attrib_list):
    """Generate field, attribute tuples from normal cards."""
    for tag in attrib_list:
        attr_tup = tag.text.split(u':\xa0 ')
        attr_tup = [x.strip() for x in attr_tup]  # Strip whitespace from k and v
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
            current_row = (row_items[0], '{} --> {}'.format(row_items[1], row_items[2]))
            row_items = []
            yield current_row


def get_cards(soup):
    """Parse all cards and add to listing dictionary."""
    house_data = {}
    # Get list of card tags
    result = soup.find_all('div', attrs={'class': 'card'})

    # First card, no title (basic info)
    tag_basic_info = result[0]
    basic_info_list = tag_basic_info.find_all('div', class_='col-12')
    house_data['basic_info'] = house_data.setdefault('basic_info', {})
    for i in basic_info_list:
        attr_tup = tuple(i.text.split(u':\xa0 '))
        house_data['basic_info'] = dict([attr_tup])

    # All good cards
    for i in result:
        card_head = i.find('div', class_='card-header')
        if card_head:
            card_title = card_head.string
            if card_title:
                discard = ['which', 'open houses', 'questions']
                if any(x in card_title.lower() for x in discard):
                    continue
                card_title = card_title.lower().strip()
                card_title = card_title.replace(' ', '_')

                # Create the key, in case names change or it's new
                house_data.setdefault(card_title, {})
                card_attrib_list = i.find_all('div', class_='col-12')
                if card_attrib_list:
                    for field_attrib in scrape_normal_card(card_attrib_list):
                        house_data[card_title].update([field_attrib])
                if not card_attrib_list:  # the Listing History card
                    card_attrib_list = i.find_all('div', class_='col-4')
                    for row in scrape_history_card(card_attrib_list):
                        house_data[card_title].update({row[0]: row[1]})
    return house_data


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
    house['data'] = get_cards(soup)
    return house


def scrape_from_url_list(url_df, quiet=True):
    """Given an array of URLs, use soup scraper to save JSONs of the listing data."""
    options = Options()
    if quiet:
        options.headless = True

    with webdriver.Firefox(options=options, executable_path=Code.GECKODRIVER_PATH) as wd:
        print('Opening browser and signing in...')
        sign_into_website(wd)
        print('Navigating to URLs...\n')
        for row in url_df.itertuples():
            random.seed()
            wait_time = random.random() * 5

            # Check if URL is still valid
            result_code = support.check_status_of_website(row.url)
            if result_code != 200:
                print('URL did not return valid response code.')
                continue

            # Get soup, then scrape and wait before moving on
            try:
                soup = get_soup_for_url(row.url, wd)
            except ListingNotAvailable as e:
                print('\t{}'.format(e))
                continue
            except TimeoutException as e:
                print('\t{}'.format(e))
                continue
            listing_dict = scrape_soup(soup)

            # Add a couple more fields
            listing_dict['_metadata'].update({'URL': row.url})
            listing_dict['_metadata'].update({'date_added': row.date_added})

            # Merge with previous dict
            json_handling.check_and_merge_dicts(listing_dict)

            json_handling.add_dict_to_json(listing_dict)
            print('Waiting {:.1f} seconds...'.format(wait_time))
            sleep(wait_time)
            gc.collect()


if __name__ == '__main__':
    sample_url_list = [keys.sample_url, keys.sample_url2, keys.sample_url3]
    sample_house = House(url=sample_url_list[0])

    #google_creds = google_sheets.get_creds()
    #sample_urls = google_sheets.get_url_list(google_creds).tail(1)
    #sample_house = House(url=sample_urls.iloc[0]['url'], added_date=sample_urls.iloc[0]['date_added'])

    options = Options()
    options.headless = True
    with webdriver.Firefox(
            options=options,
            executable_path=Code.GECKODRIVER_PATH) as wd:
        print('Opening browser and signing in...')
        sign_into_website(wd)
        sample_house.scrape(wd)
        print(json.dumps(sample_house['listing'], indent=2))
