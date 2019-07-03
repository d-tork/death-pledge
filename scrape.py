"""Scrape listings for data I would normally input myself."""

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup

options = Options()
options.headless = True  # to invoke, add options=options to the webdriver call
browser = webdriver.Firefox()
url = r"https://daniellebiegner.realscout.com/homesearch/listings/p-10217-rolling-green-way-fort-washington-20744-brightmls-158"
browser.get(url)
html_source = browser.page_source

soup = BeautifulSoup(html_source, features='html.parser')
tags = soup.html.find_all('a', 'show-more-details')
browser.find_element_by_class_name('show-more-details').click()

home_dict = {}
home_dict['sale_price'] = soup.find('p', 'price').contents[0]
home_dict['list_price'] = soup.find('p', 'price-listed').contents[0]
home_dict['status'] = soup.find('p', 'status').contents[0]

for k, v in home_dict.items():
    print('{}: {}'.format(k, v))

browser.quit()
