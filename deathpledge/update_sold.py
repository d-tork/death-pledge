"""Allow for manually plugging in sold home data."""
import pandas as pd
from googleapiclient.discovery import build
import logging
from time import sleep

import deathpledge
from deathpledge.api_calls import google_sheets as gs
from deathpledge import database, support

logger = logging.getLogger(__name__)


def update_sold(google_creds, db_client):
    """Get manual changes from google sheet and send to DB."""
    sold_df = get_sold_dataframe(google_creds)
    updated_rows = sold_df.loc[sold_df['sold'].notna() & sold_df['sale_price'].notna()]
    push_changes_to_db(updated_rows, db_client=db_client)


def get_sold_dataframe(google_creds):
    """Get updated sale info from google sheet

    Args:
        google_creds: pickled credentials

    Returns:
        pd.DataFrame: URL data

    """
    google_sheets_rows = gs.get_google_sheets_rows(google_creds, sheet_range='sold_range')
    google_df = pd.DataFrame.from_records(data=google_sheets_rows)
    # Set first row as headers
    google_df = google_df.rename(columns=google_df.iloc[0]).drop(google_df.index[0])
    return google_df


def push_changes_to_db(sold_df, db_client):
    """Update database docs with sold date and price."""
    clean_db = db_client[deathpledge.DATABASE_NAME]
    for row in sold_df.itertuples(index=False):
        try:
            db_doc = clean_db[row.mls_number]
        except KeyError:
            logger.error(f'{row.mls_number} not found in database, cannot update')
            continue
        if row.sale_price & row.sold:
            db_doc['sale_price'] = row.sale_price
            sold_date = support.coerce_date_string_to_date(row.sold)
            db_doc['sold'] = sold_date.strftime(deathpledge.TIMEFORMAT)
            db_doc.save()
            logger.info(f'Sale info updated in doc {row.mls_number}')
            sleep(2)


def refresh_sold_list(google_creds, db_client):
    """Push document list from db back to URL sheet."""
    logger.info('Refreshing Google sheet with view from database')
    sold_view = database.get_view(client=db_client, view='soldList')
    sold_df = create_sold_df_for_gsheet(sold_view)
    sold_list = gs.convert_dataframe_to_list(sold_df)
    empty_rows = [[''] * 10] * 500
    sold_list.extend(empty_rows)

    # Send to google
    service = build('sheets', 'v4', credentials=google_creds, cache_discovery=False)
    url_obj = dict(
        range=gs.SPREADSHEET_DICT['sold_range'],
        majorDimension='ROWS',
        values=sold_list)
    response = service.spreadsheets().values().batchUpdate(
        spreadsheetId=gs.SPREADSHEET_DICT['spreadsheetId'],
        body=dict(
            valueInputOption='USER_ENTERED',
            includeValuesInResponse=False,
            data=[
                url_obj
            ])
    ).execute()
    logger.info(response)


def create_sold_df_for_gsheet(sold_view: dict) -> pd.DataFrame:
    """Create a dataframe from the results of the database view."""
    df = pd.DataFrame.from_dict(
        sold_view, orient='index',
        columns=['added_date', 'mls_number', 'full_address', 'list_price']
    )
    df['added_date'] = pd.to_datetime(df['added_date']).dt.strftime('%m/%d/%Y')
    df = df.set_index('added_date')
    return df


def test_fill():
    import deathpledge
    google_creds = gs.GoogleCreds(
        creds_dict=deathpledge.keys.get('Google_creds')
    ).creds

    with database.DatabaseClient() as cloudant:
        refresh_sold_list(google_creds, db_client=cloudant)


if __name__ == '__main__':
    gcreds = gs.GoogleCreds(
        creds_dict=deathpledge.keys.get('Google_creds')
    ).creds
    with database.DatabaseClient() as cloudant:
        update_sold(google_creds=gcreds, db_client=cloudant)
        refresh_sold_list(google_creds=gcreds, db_client=cloudant)
