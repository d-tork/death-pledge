"""
Module for checking for new or changed listings (not a full scrape)
"""
from collections import namedtuple
import logging

import deathpledge
from deathpledge.api_calls import homescout as hs
from deathpledge import support, database, cleaning, scrape2, classes

logger = logging.getLogger(__name__)


class HomeToBeChecked(object):
    """Container for checking if a homescout listing has changed.

    Args:
        card (Card): namedtuple from homescout.HomeScoutList

    """
    RevIDs = namedtuple('RevIDs', ['raw', 'clean'], defaults=[None, None])

    def __init__(self, docid, card):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self.docid = docid
        self.price = card.price
        self.status = card.status.title()
        self.url = card.url
        self.mls = card.mls
        self.exists_in_db = False
        self.changed = False

    def has_changed(self, fetched_doc):
        prev_price = fetched_doc.get('list_price')
        price_changed = self._get_price_change(prev_price=prev_price)

        prev_status = fetched_doc.get('status')
        status_changed = self._get_status_change(prev_status=prev_status)
        return any([price_changed, status_changed])

    def _get_price_change(self, prev_price: float) -> bool:
        current_price = cleaning.parse_number(self.price)
        price_changed = not (prev_price == current_price)
        if price_changed:
            pct_change = (current_price - prev_price) / prev_price
            self.logger.info(f'Price change for {self.mls}: {pct_change:+.1%}')
        return price_changed

    def _get_status_change(self, prev_status: str):
        status_changed = not (prev_status.lower() == self.status.lower())
        if status_changed:
            self.logger.info(f'Status change for {self.mls}: {prev_status} -> {self.status}')
        return status_changed


def get_gallery_cards(max_pages, **kwargs) -> list:
    with scrape2.SeleniumDriver(**kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)

        listing_pages = homescout.collect_listings(max_pages=max_pages)
        all_cards = []
        for page in listing_pages:
            cards = page.scrape_page()
            all_cards.extend(cards)
    return all_cards


def get_docids_for_gallery_cards(cards: list) -> dict:
    """Set docid to MLS from gallery card.

    A somewhat redundant step of copying a field, but this is to ensure
    consistency with the old methods that refer to docid, rather than
    to MLS number.
    """
    listings = {}
    for card in cards:
        docid = support.create_house_id(card.mls)
        listings[docid] = card
    return listings


def check_cards_for_changes(cards: dict) -> list:
    """Bulk fetch docs from database and check for changes.

    Args:
        cards: Gallery card details by docid

    Returns:
        list: HomesToBeChecked, which have been checked and whose 'changed'
            status has been set.

    """
    docids_to_fetch = list(cards.keys())
    with database.DatabaseClient() as cloudant:
        fetched_clean_docs = database.get_bulk_docs(
            doc_ids=docids_to_fetch, db_name=deathpledge.DATABASE_NAME, client=cloudant
        )
    checked_cards = []
    for docid, card in cards.items():
        homecard = HomeToBeChecked(docid=docid, card=card)
        try:
            clean_doc = fetched_clean_docs.get(docid).get('doc')
        except (KeyError, AttributeError):  # docid not in db
            pass
        else:
            if clean_doc is None:  # docid is in db, but deleted
                pass
            else:
                homecard.exists_in_db = True
                if homecard.has_changed(clean_doc):
                    homecard.changed = True
        finally:
            checked_cards.append(homecard)
    return checked_cards


def get_cards_from_hs_gallery(max_pages, **kwargs) -> list:
    cards = get_gallery_cards(max_pages=max_pages, **kwargs)
    cards_by_docid = get_docids_for_gallery_cards(cards=cards)
    checked_cards = check_cards_for_changes(cards_by_docid)
    return checked_cards


def check_urls_for_changes(urls) -> list:
    """Check active listings in google sheet for changes in price or status.

    Args:
        urls (pd.DataFrame): URLs still active in google sheet

    Returns:
        list: Home instances which have been updated with new information.

    """
    docids_to_fetch = urls['docid'].tolist()
    with database.DatabaseClient() as cloudant:
        fetched_clean_docs = database.get_bulk_docs(
            doc_ids=docids_to_fetch, db_name=deathpledge.DATABASE_NAME, client=cloudant
        )
    checked_homes = []
    scraped_homes, sold_homes = scrape2.scrape_from_url_df(urls=urls)
    for current_home in scraped_homes + sold_homes:
        try:
            database_doc = fetched_clean_docs.get(current_home.docid).get('doc')
        except (KeyError, AttributeError):
            logger.warning(f'docid {current_home.docid} should be in clean database, but is not')
            continue
        else:
            if database_doc is None:
                logger.warning(f'docid {current_home.docid} in db, but deleted')
                continue
            else:
                current_home.clean()
                database_doc.update(current_home)
                support.update_modified_date(database_doc)
                logger.debug('check here that database_doc is now "closed" if probably sold')
                checked_homes.append(database_doc)
    return checked_homes


if __name__ == '__main__':
    from deathpledge.classes import Home

    sample_home = Home(added_date='1/18/2021', docid='VAAR175062')
    with deathpledge.database.DatabaseClient() as cloudant:
        sample_home.fetch(db_name=deathpledge.DATABASE_NAME, db_client=cloudant)
