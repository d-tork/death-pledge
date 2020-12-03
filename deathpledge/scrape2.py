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

import deathpledge
from deathpledge import support, classes
from deathpledge import realscout as rs

logger = logging.getLogger(__name__)


class SeleniumDriver(object):
    _options = firefox.options.Options()
    _geckodriver_path = deathpledge.GECKODRIVER_PATH

    def __init__(self, quiet=True):
        """Context manager for Firefox.

        Args:
            quiet (bool): Whether to hide (True) or show (False) web browser as it scrapes.

        """
        self._geckodriver_version = None
        self._options.headless = quiet
        self.webdriver = webdriver.Firefox(options=self._options, executable_path=self._geckodriver_path)

    def __enter__(self):
        self.webdriver.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        try:
            self.webdriver.__exit__(self, type, value, traceback)
        except Exception as e:
            logger.exception('Webdriver failed to exit.')

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


def scrape_from_url_df(urls, force_all, *args, **kwargs):
    """Given an array of URLs, create house instances and scrape web data.

    Args:
        urls (URLDataFrame): DataFrame-like object holding Google sheet rows
        force_all (bool): Whether to scrape all listings from the web, even if listing is Closed

    Returns:
        list: Array of home instances.

    """
    with SeleniumDriver(*args, **kwargs) as wd:
        realscout = rs.RealScoutWebsite(webdriver=wd.webdriver)
        realscout.sign_into_website()

        logger.info('Navigating to URLs')
        for row in urls.df.itertuples(index=False):
            if not url_is_valid(row.url):
                continue
            current_home = classes.Home(**row._asdict())
            current_home.fetch(db_name=deathpledge.RAW_DATABASE_NAME)
            skip_web_scrape_if_closed(current_home)
            if current_home.skip_web_scrape and not force_all:
                logger.debug('Instance property "skip_web_scrape" set to True, will not scrape.')
                continue
            current_home.scrape(website_object=realscout)
            current_home.upload(db_name=deathpledge.RAW_DATABASE_NAME)


def url_is_valid(url):
    result_code = support.check_status_of_website(url)
    if result_code != 200:
        logger.error(f'URL {url} did not return valid response code.')
        return False
    return True


def skip_web_scrape_if_closed(home):
    if home.get('status') == 'Closed':
        home.skip_web_scrape = True

