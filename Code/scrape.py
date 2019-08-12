"""Scrape listings for data I would normally input myself.

This module is deprecated as of 11 Aug 2019, due to a site
update that rendered all the previous scraping functions
obsolete.
"""

import os
import sys
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from Code.api_calls import keys

VITALS = ['bed', 'bath', 'sqft']
BASIC_INFO = ['address', 'city', 'price', 'price-listed', 'status']
DETAILS = ['Status', 'Structure Type', 'Architectural Style', 'Year Built',
           'Lot Size Acres', 'County', 'MLS Number', 'Price Per SQFT', 'HOA Fee']
ALL_ATTRIBS = VITALS + BASIC_INFO + DETAILS


def get_browser():
    """Start the browser"""
    options = Options()
    options.headless = True  # to invoke, add options=options to the webdriver call
    driver = webdriver.Firefox(executable_path=os.path.join('Drivers', 'geckodriver'))
    return driver


def get_attribute(soup_obj, attribute):
    """Retrieve specified attribute from soup."""
    if attribute in VITALS:
        num = VITALS.index(attribute)
        item = soup_obj.select_one('ul.vitals')
        return item.get_text().strip().split('     ')[num]
    elif attribute in BASIC_INFO:
        item = soup_obj.select_one('.{}'.format(attribute))
        try:
            return str(item.contents[0]).strip()
        except IndexError:
            try:
                # Avoid the hide--mobile tag which is paired with the attribute tag, but is an empty string
                item = soup_obj.find_all(attrs={'class': '{} ng-binding'.format(attribute)})[0]
                return str(item.contents[0]).strip()
            except IndexError:
                return 'Attr not found'
    elif attribute in DETAILS:
        tags = soup_obj.select('div > ul > li > p')
        for tag in tags:
            if attribute in tag.get_text():
                return str(tag.b.get_text())
    else:
        return


def get_days_since(soup_obj, mode):
    if mode == 'list':
        item = soup_obj.find_all(attrs={'count': 'property.days_on_market'})[0].get_text()
        num = int(item.split()[3])
    elif mode == 'sold':
        item = soup_obj.find_all(attrs={'class': 'days-sold'})[0].get_text()
        num = item.split()[1]
    return num


def get_details(soup_obj):
    """Generates a dictionary of the MLS details"""
    items = soup_obj.find_all('li', attrs={'ng-repeat': 'detail in details'})
    details_d = {}
    for tag in items:
        tag_str = tag.string.strip()
        tag_key = tag_str[:tag_str.find(':')]
        tag_val = tag_str[tag_str.find(':')+2:]
        try:
            tag_val = int(tag_val)
        except ValueError:  # not coercable to int
            pass
        details_d[tag_key] = tag_val
    return details_d


def get_data_from_soup(soup, url):
    home_dict = {'URL': url}

    for i in ALL_ATTRIBS:
        home_dict[i] = get_attribute(soup, i)

    # Get date of sale if sold, days listed otherwise
    if home_dict.get('status') == 'Sold':
        home_dict['date-sold'] = get_days_since(soup, 'sold')
    else:
        home_dict['days-listed'] = get_days_since(soup, 'list')

    # Get the rest of "more details"
    details_dict = get_details(soup)
    home_dict.update(details_dict)
    return home_dict


if __name__ == '__main__':

    URL = keys.sample_url
    browser = get_browser()
    sample_soup = get_soup_for_url(URL, driver=browser)
    sample_dict = get_data_from_soup(sample_soup, URL)

    # Show Them!
    for k, v in sample_dict.items():
        print('{}: {}'.format(k, v))

    browser.quit()

