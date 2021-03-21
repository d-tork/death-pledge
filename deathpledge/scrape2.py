"""Scrape listing URLs for details that I would normally input myself.

This module returns no values; it is meant to accumulate a listing's
details in a dictionary, then write that dictionary to a JSON file
(or append the dict to the list of JSON dictionaries if the file already
exists).

"""
from selenium import webdriver
from selenium.webdriver import firefox
import logging
import subprocess
import random
from time import sleep
from datetime import datetime

import deathpledge
from deathpledge import support, classes, cleaning
from deathpledge.api_calls import homescout as hs, check

logger = logging.getLogger(__name__)


class SeleniumDriver(object):
    _options = firefox.options.Options()
    _geckodriver_path = deathpledge.GECKODRIVER_PATH

    def __init__(self, quiet=True):
        """Context manager for Firefox.

        Args:
            quiet (bool): Whether to hide (True) or show (False) web browser as it scrapes.

        """
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self._geckodriver_version = None
        self._options.headless = quiet
        self.webdriver = webdriver.Firefox(options=self._options, executable_path=self._geckodriver_path)

    def __enter__(self):
        self.webdriver.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.webdriver.__exit__(self, exc_type, exc_value, traceback)
        except Exception:
            self.logger.exception('Webdriver failed to exit.')

    @property
    def geckodriver_version(self):
        return self._geckodriver_version

    @geckodriver_version.setter
    def geckodriver_version(self):
        """SO 50359334"""
        output = subprocess.run(
            [self._geckodriver_path, '-V'],
            stdout=subprocess.PIPE,
            encoding='utf-8')
        self._geckodriver_version = output.stdout.splitlines()[0]


def scrape_from_url_df(urls, *args, **kwargs) -> tuple:
    """Given an array of URLs, create house instances and scrape web data.

    Args:
        urls (DataFrame): DataFrame-like object holding Google sheet rows.
        *args, **kwargs: passed to SeleniumDriver.

    Returns: tuple
        list: scraped home instances
        list: homes which failed the scrape because they are probably sold

    """
    scraped_homes = []
    closed_homes = []
    with SeleniumDriver(*args, **kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)

        for row in urls.itertuples(index=False):
            if not url_is_valid(row.url):
                logger.warning(f'URL {row.url} is not valid')
                continue
            current_home = classes.Home(**row._asdict())
            try:
                current_home.scrape(website_object=homescout)
            except hs.HomeSoldException:
                logger.warning(f'URL {row.url} is already sold.')
                current_home['probably_sold'] = True
                closed_homes.append(current_home)
                continue
            except:
                logger.exception(f'Scrape failed for {row.url}')
                continue
            else:
                current_home.docid = support.create_house_id(current_home['mls_number'])
                scraped_homes.append(current_home)
    return scraped_homes, closed_homes


def scrape_from_homescout_gallery(db_client, max_pages: int, *args, **kwargs):
    cards = check.get_cards_from_hs_gallery(max_pages=max_pages, **kwargs)
    clean_db = db_client[deathpledge.DATABASE_NAME]
    with SeleniumDriver(*args, **kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)
        new_homes = []
        for card in cards:
            if card.exists_in_db:
                if card.changed:
                    # update clean in place
                    sleep(10)
                    try:
                        clean_doc = clean_db[card.docid]
                        clean_doc['list_price'] = cleaning.parse_number(card.price)
                        clean_doc['status'] = card.status
                        clean_doc['scraped_time'] = datetime.now().strftime(deathpledge.TIMEFORMAT)
                        clean_doc.save()
                    except KeyError:
                        pass
                else:
                    pass
            else:
                current_home = classes.Home(url=card.url, docid=card.docid)
                try:
                    current_home.scrape(website_object=homescout)
                    wait_a_random_time()
                except:
                    logger.error('Scraping failed for {card.url}', exc_info=True)
                else:
                    new_homes.append(current_home)
    return new_homes


def wait_a_random_time():
    seconds_to_wait = random.randint(1, 10)
    sleep(seconds_to_wait)


def url_is_valid(url):
    result_code = support.check_status_of_website(url)
    if result_code != 200:
        logger.error(f'URL {url} did not return valid response code.')
        return False
    return True
