"""Run actions on housing search spreadsheet."""

from datetime import datetime
from Code.api_calls import google_sheets, bing, citymapper
from Code import scrape2


def get_coords_and_commute(df):
    """Translate address to geographic coordinates and ping Citymapper for commute time."""
    print('Getting coordinates from address...')
    df['coords'] = df['full_address'].apply(bing.get_coords)
    print('Done')
    print('Getting commute times from coordinates...')
    df['cm_time'] = df['coords'].apply(citymapper.get_citymapper_commute_time())
    return df


if __name__ == '__main__':
    start_time = datetime.now()
    print(start_time)

    urls = google_sheets.get_url_list()

    # Get full df
    df_full = scrape2.scrape_from_url_list(urls)
    # TESTING:
    #df_full = scrape2.scrape_from_url_list(urls.head(3))

    # Add commute times
    #df_full = get_coords_and_commute(df_full)

