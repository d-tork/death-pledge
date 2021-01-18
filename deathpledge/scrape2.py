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


def scrape_from_url_df(urls, db_client, *args, **kwargs):
    """Given an array of URLs, create house instances and scrape web data.

    Args:
        urls (DataFrame): DataFrame-like object holding Google sheet rows
        db_client (Cloudant.iam): Cloudant session client.
        *args, **kwargs: passed to SeleniumDriver

    Returns:
        list: Array of home instances.

    """
    with SeleniumDriver(*args, **kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)
        homescout.sign_into_website()

        for row in urls.itertuples(index=False):
            if not url_is_valid(row.url):
                continue
            current_home = classes.Home(**row._asdict())
            if current_home.skip_web_scrape:
                logger.debug('Instance property "skip_web_scrape" set to True, will not scrape.')
                continue
            try:
                current_home.scrape(website_object=homescout)
            except:
                continue
            current_home.upload(db_name=deathpledge.RAW_DATABASE_NAME, db_client=db_client)


def scrape_from_homescout_gallery(db_client, max_pages: int, *args, **kwargs):
    cards = check.main(max_pages=max_pages, **kwargs)
    with SeleniumDriver(*args, **kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)
        for card in cards:
            if not card.exists:
                current_home = classes.Home(url=card.url, docid=card.docid)
                try:
                    current_home.scrape(website_object=homescout)
                except:
                    raise
                current_home.upload(db_name=deathpledge.RAW_DATABASE_NAME, db_client=db_client)
            else:
                if card.changed:
                    pass  # TODO: execute procedure for updating raw database record


def url_is_valid(url):
    result_code = support.check_status_of_website(url)
    if result_code != 200:
        logger.error(f'URL {url} did not return valid response code.')
        return False
    return True
