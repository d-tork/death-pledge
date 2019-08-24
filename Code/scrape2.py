"""
Scrape listing URLs for details that I would normally input myself.

This module returns no values; it is meant to accumulate a listing's
details in a dictionary, then write that dictionary to a JSON file
for that listing (or append the dict to the list of JSON dictionaries
if the file already exists) with a key:value pair for the timestamp
of access.

"""
import random
import gc
from datetime import datetime
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import Code
from Code import support, clean, json_handling, modify
from Code.api_calls import keys


class ListingNotAvailable(Exception):
    pass


def get_html_from_file(fname):
    """Gets HTML soup from a local file (for offline testing)"""
    with open(fname) as fhand:
        c = fhand.read()
    return BeautifulSoup(c, features='html.parser')


def prettify_soup(soup_obj):
    """Writes out HTML soup for manual parsing (for testing)"""
    prettyhtml = soup_obj.prettify()
    with open('html_source.txt', 'w') as fhand:
        fhand.write(prettyhtml)


def sign_into_website(driver):
    """Open website and login to access restricted listings."""
    # Sign in
    driver.get(keys.website_url)
    username = driver.find_element_by_id('email_field')
    password = driver.find_element_by_id('user_password')

    username.send_keys(keys.website_email)
    password.send_keys(keys.website_pw)
    sleep(.2)
    driver.find_element_by_name('commit').click()
    try:
        element = WebDriverWait(driver, 60).until(
            EC.title_contains('My Matches'))
    except TimeoutException:
        print('Failed to login.')


def get_soup_for_url(url, driver):
    """Get BeautifulSoup object for single URL"""
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

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return soup


def get_main_box(soup, dic):
    """Add scrape_soup box details to listing dictionary."""
    # Get tags
    result = soup.find_all('div', attrs={'class': 'col-8 col-sm-8 col-md-7'})
    main_box = result[0]

    # Extract strings from tags
    badge = main_box.a.string
    address = main_box.h1.string
    citystate = main_box.h2.string
    vitals = main_box.h3.string.split(' - ')

    # Add to dictionary
    dic['_info'] = {'badge': badge,
                    'address': address,
                    'city_state': citystate,
                    'full_address': ' '.join([address, citystate]),
                    'beds': vitals[0],
                    'baths': vitals[1],
                    'sqft': vitals[2]}

    for i in [address, citystate, vitals, badge]:
        print('\t{}'.format(i))


def get_price_info(soup, dic):
    """Add price info details to listing dictionary."""
    # Get tags
    result = soup.find_all('div', attrs={'class': 'col-4 col-sm-4 col-md-5 text-right'})
    box = result[0]
    price = box.h2.text
    dic['_info'].update({'list_price': price})

    try:
        badge = box.p
        if 'sold' in badge.text.lower():
            date_sold = badge.text.split(': ')[-1]
            list_price = box.small.text.split()[-1]
            dic['_info'].update({'sold': date_sold,
                                'sale_price': price,
                                'list_price': list_price})
    except AttributeError:
        # Most likely "Off Market"
        pass


def scrape_normal_card(attrib_list):
    """Generate field, attribute tuples from normal cards."""
    for tag in attrib_list:
        attr_tup = tag.text.split(u':\xa0 ')
        attr_tup = [x.strip() for x in attr_tup]  # Strip whitespace from k and v
        yield attr_tup


def scrape_history_card(attrib_list):
    """Generate rows from the Listing History table.

    :returns named tuple
    """
    row_items = []
    for i, tag in enumerate(attrib_list):
        val = tag.text.strip()
        row_items.append(val)
        if (i + 1) % 3 == 0:  # Third (last) item)
            current_row = (row_items[0], '{} --> {}'.format(row_items[1], row_items[2]))
            row_items = []
            yield current_row


def get_cards(soup, dic):
    """Parse all cards and add to listing dictionary."""
    # Get list of card tags
    result = soup.find_all('div', attrs={'class': 'card'})

    # First card, no title (basic info)
    tag_basic_info = result[0]
    basic_info_list = tag_basic_info.find_all('div', class_='col-12')
    for i in basic_info_list:
        attr_tup = tuple(i.text.split(u':\xa0 '))
        dic['basic info'].update(dict([attr_tup]))

    # All good cards
    for i in result:
        card_head = i.find('div', class_='card-header')
        if card_head:
            card_title = card_head.string
            if card_title:
                discard = ['Which', 'Open Houses']
                if any(x in card_title for x in discard):
                    continue
                card_title = card_title.lower().strip()

                # Create the key, in case names change or it's new
                dic.setdefault(card_title, {})
                card_attrib_list = i.find_all('div', class_='col-12')
                if card_attrib_list:
                    for field_attrib in scrape_normal_card(card_attrib_list):
                        dic[card_title].update([field_attrib])
                if not card_attrib_list:  # the Listing History card
                    card_attrib_list = i.find_all('div', class_='col-4')
                    for row in scrape_history_card(card_attrib_list):
                        dic[card_title].update({row[0]: row[1]})


def scrape_soup(soup):
    """Scrape all for a single BS4 soup object.

    :returns dict
    """
    # Initialize dict with date record
    listing_dict = support.initialize_listing_dict()
    listing_dict['_metadata'].update({'scraped_time': str(datetime.now())})

    # Scrape three sections
    get_main_box(soup, listing_dict)
    get_price_info(soup, listing_dict)
    get_cards(soup, listing_dict)

    return listing_dict


def scrape_from_url_list(url_list):
    """Given an array of URLs, use soup scraper to save JSONs of the listing data.

    Meant for use within a context manager for the webdriver.
    """
    with webdriver.Firefox(executable_path=Code.GECKODRIVER_PATH) as wd:
        sign_into_website(wd)
        for url in url_list:
            random.seed()
            wait_time = random.random() * 5

            # Check if URL is still valid
            result_code = support.check_status_of_website(url)
            if result_code != 200:
                print('URL did not return valid response code.')
                continue

            # Get soup, then scrape and wait before moving on
            try:
                soup = get_soup_for_url(url, wd)
            except ListingNotAvailable as e:
                print('\t{}'.format(e))
                continue
            except TimeoutException as e:
                print('\t{}'.format(e))
                continue
            listing_dict = scrape_soup(soup)

            # Clean and add a couple more fields
            clean.main(listing_dict)
            listing_dict['_metadata'].update({'URL': url})

            # Merge with previous dict
            json_handling.check_and_merge_dicts(listing_dict)

            json_handling.add_dict_to_json(listing_dict)
            print('Waiting {:.1f} seconds...'.format(wait_time))
            sleep(wait_time)
            gc.collect()


if __name__ == '__main__':
    sample_url_list = [keys.sample_url, keys.sample_url2, keys.sample_url3]
    sample_url_list = [keys.sample_url4]
    scrape_from_url_list(sample_url_list)
