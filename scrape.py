"""Scrape listings for data I would normally input myself."""

import os
import re
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup


def get_soup(url):
    """Start the browser, navigate to URL, click more details, return soup"""
    options = Options()
    options.headless = True  # to invoke, add options=options to the webdriver call
    driver = webdriver.Firefox()
    driver.get(url)
    driver.find_element_by_class_name('show-more-details').click()
    return BeautifulSoup(driver.page_source, 'html.parser'), driver


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
    items = soup.find_all('li', attrs={'ng-repeat': 'detail in details'})
    details_d = {}
    for tag in items:
        tag_str = tag.string.strip()
        tag_key = tag_str[:tag_str.find(':')]
        tag_val = tag_str[tag_str.find(':')+2:]
        details_d[tag_key] = tag_val
    return details_d



if __name__ == '__main__':

    URL = r"https://daniellebiegner.realscout.com/homesearch/listings/p-10217-rolling-green-way-fort-washington-20744-brightmls-158"
    soup, browser = get_soup(URL)

    home_dict = {}

    vitals = ['bed', 'bath', 'sqft']
    meta = ['address', 'city', 'price', 'price-listed', 'status']
    details = ['Status', 'Structure Type', 'Architectural Style', 'Year Built',
               'Lot Size Acres', 'County', 'MLS Number', 'Price Per SQFT', 'HOA Fee']
    all_attribs = vitals + meta + details

    for i in all_attribs:
        home_dict[i] = get_attribute(soup, i)

    details_dict = get_details(soup)
    home_dict.update(details_dict)
    # home_dict_final = {**home_dict, **details_dict}

    # Show Them!
    for k, v in home_dict.items():
        print('{}: {}'.format(k, v))

    browser.quit()

