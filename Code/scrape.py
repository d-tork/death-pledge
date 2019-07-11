"""Scrape listings for data I would normally input myself."""

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

vitals = ['bed', 'bath', 'sqft']
meta = ['address', 'city', 'price', 'price-listed', 'status']
details = ['Status', 'Structure Type', 'Architectural Style', 'Year Built',
           'Lot Size Acres', 'County', 'MLS Number', 'Price Per SQFT', 'HOA Fee']
ALL_ATTRIBS = vitals + meta + details


def get_browser():
    """Start the browser"""
    options = Options()
    options.headless = True  # to invoke, add options=options to the webdriver call
    driver = webdriver.Firefox(executable_path=os.path.join('Drivers', 'geckodriver'))

    # Sign in
    driver.get(r'https://daniellebiegner.realscout.com/users/sign_in')
    try:
        element = WebDriverWait(driver, 60).until(
            EC.text_to_be_present_in_element_value((By.CLASS_NAME, 'link-button'), 'My homes'))
    except TimeoutException:
        print('Failed to login. No credentials provided.')
    return driver


def get_attribute(soup_obj, attribute):
    """Retrieve specified attribute from soup."""
    vitals = ['bed', 'bath', 'sqft']
    meta = ['address', 'city', 'price', 'price-listed', 'status']
    details = ['Status', 'Structure Type', 'Architectural Style', 'Year Built',
               'Lot Size Acres', 'County', 'MLS Number', 'Price Per SQFT', 'HOA Fee']

    if attribute in vitals:
        num = vitals.index(attribute)
        item = soup_obj.select_one('ul.vitals')
        return item.get_text().strip().split('     ')[num]
    elif attribute in meta:
        item = soup_obj.select_one('.{}'.format(attribute))
        return str(item.contents[0]).strip()
    elif attribute in details:
        tags = soup_obj.select('div > ul > li > p')
        for tag in tags:
            if attribute in tag.get_text():
                return str(tag.b.get_text())
    else:
        return


def get_details(soup_obj):
    """Generates a dictionary of the MLS details"""
    items = soup_obj.find_all('li', attrs={'ng-repeat': 'detail in details'})
    details_d = {}
    for tag in items:
        tag_str = tag.string.strip()
        tag_key = tag_str[:tag_str.find(':')]
        tag_val = tag_str[tag_str.find(':')+2:]
        details_d[tag_key] = tag_val
    return details_d


def get_full_data_for_url(url, driver, click_wait_time=3.1415):
    """Get dict of all values for a single URL"""
    url_suffix = url.rfind('/')+3
    print('URL: {}'.format(url[url_suffix:]))
    driver.get(url)
    if 'Listing not found' in driver.page_source:
        return None
    sleep(click_wait_time)
    try:
        element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'show-more-details'))
        )
        driver.find_element_by_class_name('show-more-details').click()
    except TimeoutException:
        return None
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    home_dict = {'URL': url}

    for i in ALL_ATTRIBS:
        home_dict[i] = get_attribute(soup, i)

    details_dict = get_details(soup)
    home_dict.update(details_dict)
    return home_dict


if __name__ == '__main__':

    URL = r"https://daniellebiegner.realscout.com/homesearch/listings/p-10217-rolling-green-way-fort-washington-20744-brightmls-158"
    browser = get_browser()
    sample_dict = get_full_data_for_url(URL, driver=browser)

    # Show Them!
    for k, v in sample_dict.items():
        print('{}: {}'.format(k, v))

    browser.quit()

