import pandas as pd

from deathpledge.scrape2 import SeleniumDriver
from deathpledge.api_calls import homescout as hs

with SeleniumDriver(quiet=False) as wd:
    homescout = hs.HomeScoutWebsite(webdriver=wd.webdriver)
    homescout.sign_into_website()

    listing_pages = homescout.collect_listings(max_pages=5)
    all_cards = []
    for page in listing_pages:
        cards = page.scrape_page()
        all_cards.extend(cards)

    df = pd.DataFrame(all_cards)
    print('wait here')
