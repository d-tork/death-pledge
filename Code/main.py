"""Run actions on housing search spreadsheet."""

from Code.api_calls import google_sheets, keys
from Code import scrape2, score2, modify

# Scrape all URLs from google
# Re-scrape all on-market JSONS
# Supplement all
# Score all
# Pull from Google
# Push all to Google


def main():
    urls = google_sheets.get_url_list()
    scrape2.scrape_from_url_list(urls)
    modify.main()
    score2.main()


def single_sample():
    url_list = [keys.sample_url4]
    scrape2.scrape_from_url_list(url_list)


if __name__ == '__main__':
    main()
    # single_sample()
