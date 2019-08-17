"""
Scrape listing URLs for details that I would normally input myself.

This module returns no values; it is meant to accumulate a listing's
details in a dictionary, then write that dictionary to a JSON file
for that listing (or append the dict to the list of JSON dictionaries
if the file already exists) with a key:value pair for the timestamp
of access.

"""
import os
import json
import random
import gc
from datetime import datetime
from time import sleep
from collections import namedtuple
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from django.utils.text import slugify
import Code
from Code import support, clean, modify
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


def get_soup_for_url(url, driver, click_wait_time=3.1415):
    """Get BeautifulSoup object for single URL"""
    url_suffix = url.rfind('/')+3
    print('URL: {}'.format(url[url_suffix:]))
    driver.get(url)

    if 'Listing unavailable.' in driver.page_source:
        raise ListingNotAvailable("Bad URL or listing no longer exists.")
    sleep(click_wait_time)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return soup


def get_main_box(soup, dic):
    """Add scrape_soup box details to listing dictionary."""
    # Get tags
    result = soup.find_all('div', attrs={'class': 'col-8 col-sm-8 col-md-7'})
    try:
        main_box = result[0]
    except KeyError:
        sleep(3)
        main_box = result[0]

    # Extract strings from tags
    badge = main_box.a.string
    address = main_box.h1.string
    citystate = main_box.h2.string
    vitals = main_box.h3.string.split(' - ')

    # Add to dictionary
    dic['info'] = {'badge': badge,
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
    dic['info'].update({'list_price': price})

    # TODO: get days on site

    try:
        badge = box.p
        if 'sold' in badge.text.lower():
            date_sold = badge.text.split(': ')[-1]
            list_price = box.small.text.split()[-1]
            dic['info'].update({'sold': date_sold,
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
    Row = namedtuple('Row', ['date', 'start', 'end'])
    row_items = []
    for i, tag in enumerate(attrib_list):
        val = tag.text.strip()
        row_items.append(val)
        if (i + 1) % 3 == 0:  # Third (last) item)
            current_row = Row._make(row_items)
            row_items = []
            yield current_row


def get_cards(soup, dic):
    """Parse all cards and add to listing dictionary."""
    # Get list of card tags
    result = soup.find_all('div', attrs={'class': 'card'})

    dic['basic_info'] = {}

    # First card, no title (basic info)
    tag_basic_info = result[0]
    basic_info_list = tag_basic_info.find_all('div', class_='col-12')
    for i in basic_info_list:
        attr_tup = tuple(i.text.split(u':\xa0 '))
        dic['basic_info'].update(dict([attr_tup]))

    # All good cards
    for i in result:
        card_head = i.find('div', class_='card-header')
        if card_head:
            card_title = card_head.string
            if card_title:
                discard = ['Which']
                if any(x in card_title for x in discard):
                    continue
                card_title = card_title.strip()

                dic[card_title] = dic.setdefault(card_title, {})  # ensure it exists
                card_attrib_list = i.find_all('div', class_='col-12')
                if card_attrib_list:
                    for field_attrib in scrape_normal_card(card_attrib_list):
                        dic[card_title].update([field_attrib])
                if not card_attrib_list:  # the Listing History card
                    card_attrib_list = i.find_all('div', class_='col-4')
                    for row in scrape_history_card(card_attrib_list):
                        dic[card_title].update({row.date: (row.start, row.end)})


def scrape_soup(soup):
    """Scrape all for a single BS4 soup object.

    :returns dict
    """
    # Initialize dict with date record
    listing_dict = {'_metadata': {'timestamp': str(datetime.now())}}

    # Scrape three sections
    sleep(1)
    # TODO: WHAT is going on here that causing it to indexerror out?
    get_main_box(soup, listing_dict)
    get_price_info(soup, listing_dict)
    get_cards(soup, listing_dict)

    return listing_dict


def add_dict_to_file(dic):
    """Write listing dict to JSON file. If file already exists, insert the dict.

    :returns list of dicts
        a list of len 1 or more of all scraped versions
    """
    # Define file path
    outname = dic['info']['address']
    outname = slugify(outname).replace('-', '_').upper()
    outfilepath = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'saved_listings',
                               '{}.json'.format(outname))

    all_scrapes = []
    # Read existing dictionaries (if file exists)
    try:
        with open(outfilepath, 'r') as f:
            contents = json.load(f)
            all_scrapes.extend(contents)
    except FileNotFoundError:
        pass

    # Check if newest scrape is different from previous one
    if all_scrapes:
        try:
            any_change = check_if_changed(dic, all_scrapes)
        except KeyError:
            any_change = True
    else:
        any_change = True
    if not any_change:
        print('\tChange in listing data: {}'.format(any_change))

    if any_change:
        # Write new (and old) dictionaries to a list in file
        all_scrapes.insert(0, dic)
        os.makedirs(os.path.dirname(outfilepath), exist_ok=True)
        with open(outfilepath, 'w') as f:
            f.write(json.dumps(all_scrapes, indent=4))

    return all_scrapes


def check_if_changed(dic1, old_list):
    dic2 = old_list[0]
    for k1, inner_dict in dic1.items():
        for k2 in [x for x in inner_dict if x != 'timestamp']:
            if inner_dict[k2] != dic2[k1][k2]:
                print('\tChanged: {}'.format(k2))
                return True
    return False


def scrape_from_url_list(url_list):
    """Given an array of URLs, use soup scraper to save JSONs of the listing data.

    Meant for use within a context manager for the webdriver.
    """
    with webdriver.Firefox(executable_path=Code.GECKODRIVER_PATH) as wd:
        sign_into_website(wd)
        for url in url_list:
            random.seed()
            wait_time = random.random()*7
            click_wait = 2 + random.random()

            # Check if URL is still valid
            result_code = support.check_status_of_website(url)
            if result_code != 200:
                print('URL did not return valid response code.')
                continue

            # Get soup, then scrape and wait before moving on
            try:
                soup = get_soup_for_url(url, wd, click_wait)
            except ListingNotAvailable as e:
                print('\t{}'.format(e))
                continue
            listing_dict = scrape_soup(soup)
            clean.main(listing_dict)

            # Add URL
            listing_dict['_metadata'].update({'URL': url})
            # Add geocoords
            modify.add_coords(listing_dict)

            listing_dicts_all = add_dict_to_file(listing_dict)
            print('Waiting {:.1f} seconds...'.format(wait_time))
            sleep(wait_time)
            gc.collect()


if __name__ == '__main__':
    filename = 'sold_sample.html'
    # filename = 'forsale_sample.html'
    #sample_soup = get_html_from_file(filename)

    with webdriver.Firefox(executable_path=Code.GECKODRIVER_PATH) as browser:
        sign_into_website(browser)
        sample_soup = get_soup_for_url(keys.sample_url3, browser)
        # prettify_soup(soup)
        scraped_dict = scrape_soup(sample_soup)
        scraped_dict['_metadata'].update({'URL': keys.sample_url3})
        clean.main(scraped_dict)
        all_dict_versions = add_dict_to_file(scraped_dict)
