"""
Module for checking for new or changed listings (not a full scrape)
"""
from collections import namedtuple
import logging

import deathpledge
from deathpledge.scrape2 import SeleniumDriver
from deathpledge.api_calls import homescout as hs, realtor
from deathpledge import support, database, cleaning

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
        self.status = card.status
        self.url = card.url
        self.mls = card.mls
        self.exists_in_db = False
        self.changed = False

    def has_changed(self, fetched_doc):
        prev_price = cleaning.parse_number(fetched_doc.get('list_price'))
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
    with SeleniumDriver(**kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)

        listing_pages = homescout.collect_listings(max_pages=max_pages)
        all_cards = []
        for page in listing_pages:
            cards = page.scrape_page()
            all_cards.extend(cards)
    return all_cards


def get_docids_for_gallery_cards(cards: list) -> dict:
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
        fetched_raw_docs = database.get_bulk_docs(
            doc_ids=docids_to_fetch, db_name=deathpledge.RAW_DATABASE_NAME, client=cloudant
        )
    checked_cards = []
    for docid, card in cards.items():
        homecard = HomeToBeChecked(docid=docid, card=card)
        try:
            raw_doc = fetched_raw_docs.get(docid).get('doc')
        except (KeyError, AttributeError):  # docid not in raw db
            pass
        else:
            if raw_doc is None:  # docid is in db, but deleted
                pass
            else:
                homecard.exists_in_db = True
                if homecard.has_changed(raw_doc):
                    homecard.changed = True
        finally:
            checked_cards.append(homecard)
    return checked_cards


def get_cards_from_hs_gallery(max_pages, **kwargs) -> list:
    cards = get_gallery_cards(max_pages=max_pages, **kwargs)
    cards_by_docid = get_docids_for_gallery_cards(cards=cards)
    checked_cards = check_cards_for_changes(cards_by_docid)
    return checked_cards


def check_home_for_sale_status(home):
    """Check address elsewhere for sale status."""
    realtor_com = realtor.RealtorWebsite()
    url = realtor_com.get_url_from_search(full_address=home.get('full_address'))
    soup = realtor_com.get_soup_for_url(url=url)
    logger.debug('stop here')


if __name__ == '__main__':
    from deathpledge.classes import Home

    sample_home = Home(added_date='1/18/2021', docid='VAAR175062')
    with deathpledge.database.DatabaseClient() as cloudant:
        sample_home.fetch(db_name=deathpledge.DATABASE_NAME, db_client=cloudant)
    check_home_for_sale_status(sample_home)
