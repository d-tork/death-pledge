"""
Module for checking for new or changed listings (not a full scrape)
"""
import deathpledge
from deathpledge.scrape2 import SeleniumDriver
from deathpledge.api_calls import homescout as hs
from deathpledge import support, database, classes


class HomeToBeChecked(object):
    """Container for checking if a homescout listing has changed.

    Args:
        card (Card): namedtuple from homescout.HomeScoutList

    """
    def __init__(self, docid, card):
        self.docid = docid
        self.price = card.price
        self.status = card.status
        self.url = card.url
        self.exists = False
        self.changed = False

    def has_changed(self, fetched_doc):
        price_changed = not(fetched_doc['list_price'] == self.price)
        status_changed = not(fetched_doc['status'] == self.status)
        return any([price_changed, status_changed])


def get_gallery_cards(max_pages, **kwargs) -> list:
    with SeleniumDriver(**kwargs) as wd:
        homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)
        homescout.sign_into_website()

        listing_pages = homescout.collect_listings(max_pages=max_pages)
        all_cards = []
        for page in listing_pages:
            cards = page.scrape_page()
            all_cards.extend(cards)
    return all_cards


def get_docids_for_gallery_cards(cards: list) -> dict:
    listings = {}
    for card in cards:
        full_address = ' '.join(
            [card.address, card.city_state_zip]
        )
        docid = support.create_house_id(full_address)
        listings[docid] = card
    return listings


def check_cards_for_changes(cards: dict) -> list:
    """Bulk fetch docs from database and check for changes."""
    docids_to_fetch = list(cards.keys())
    with database.DatabaseClient() as cloudant:
        fetched_docs = database.get_bulk_docs(
            doc_ids=docids_to_fetch,
            db_name=deathpledge.RAW_DATABASE_NAME,
            client=cloudant
        )
    checked_cards = []
    for docid, card in cards.items():
        homecard = HomeToBeChecked(docid=docid, card=card)
        try:
            doc = next((d for d in fetched_docs if d['id'] == docid))['doc']
        except (KeyError, StopIteration):
            pass
        else:
            if doc is None:  # docid is in db, but deleted
                pass
            else:
                homecard.exists = True
                if homecard.has_changed(doc):
                    homecard.changed = True
        finally:
            checked_cards.append(homecard)
    return checked_cards


def main(max_pages, **kwargs) -> list:
    cards = get_gallery_cards(max_pages=max_pages, **kwargs)
    cards_by_docid = get_docids_for_gallery_cards(cards=cards)
    checked_cards = check_cards_for_changes(cards_by_docid)
    return checked_cards


if __name__ == '__main__':
    main()
