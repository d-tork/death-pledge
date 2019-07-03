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
        # return str(item.string)
        return str(item.contents[0]).strip()
    elif attribute in details:
        tags = soup_obj.select('div > ul > li > p')
        for tag in tags:
            if attribute in tag.get_text():
                return str(tag.b.get_text())
    else:
        return


if __name__ == '__main__':

    URL = r"https://daniellebiegner.realscout.com/homesearch/listings/p-10217-rolling-green-way-fort-washington-20744-brightmls-158"
    soup, browser = get_soup(URL)

    home_dict = {}
    # home_dict['sale_price'] = soup.find('p', 'price').contents[0]
    # home_dict['list_price'] = soup.find('p', 'price-listed').contents[0]
    # home_dict['status'] = soup.find('p', 'status').contents[0]

    vitals = ['bed', 'bath', 'sqft']
    meta = ['address', 'city', 'price', 'price-listed', 'status']
    details = ['Status', 'Structure Type', 'Architectural Style', 'Year Built',
               'Lot Size Acres', 'County', 'MLS Number', 'Price Per SQFT', 'HOA Fee']
    all_attribs = vitals + meta + details

    for i in all_attribs:
        home_dict[i] = get_attribute(soup, i)

    for k, v in home_dict.items():
        print('{}: {}'.format(k, v))

    browser.quit()

