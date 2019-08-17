"""Run actions on housing search spreadsheet."""

from datetime import datetime
from Code.api_calls import google_sheets, coordinates, citymapper
from Code import scrape2


def process_url_list(df):
    """Make adjustments to URL dataframe before passing as series."""
    def trim_url(url_str):
        """Remove extra params from URL"""
        q_mark = url_str.find('?')
        if q_mark > -1:
            return url_str[:q_mark]
        else:
            return url_str

    # Trim urls to their base
    df['url'] = df['url'].apply(trim_url)

    # drop rows that I've marked inactive
    url_series = df.loc[df['inactive'] == '']['url']
    return url_series


def get_coords_and_commute(df):
    """Translate address to geographic coordinates and ping Citymapper for commute time."""
    print('Getting coordinates from address...')
    df['coords'] = df['full_address'].apply(coordinates.get_coords)
    print('Done')
    print('Getting commute times from coordinates...')
    df['cm_time'] = df['coords'].apply(citymapper.get_commute_time)
    return df


# TODO: add exception handlers

if __name__ == '__main__':
    start_time = datetime.now()
    print(start_time)

    my_creds = google_sheets.get_creds()
    df_raw = google_sheets.main(my_creds)
    urls = process_url_list(df_raw)

    # Get full df
    df_full = scrape2.scrape_from_url_list(urls)
    # TESTING:
    #df_full = scrape2.scrape_from_url_list(urls.head(3))

    # Add commute times
    #df_full = get_coords_and_commute(df_full)

