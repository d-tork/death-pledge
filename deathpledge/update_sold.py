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
    logger.info('Updating sale info from google sheet')
    sold_df = get_sold_dataframe(google_creds)
    updated_rows = sold_df.loc[
            (sold_df['sold'].notna() & sold_df['sale_price'].notna())
            | sold_df['notes'].notna()
            ]
    logger.info(f'Updated rows: {len(updated_rows)}')
    push_changes_to_db(updated_rows, db_client=db_client)


def get_sold_dataframe(google_creds):
    """Get updated sale info from google sheet

    Args:
        google_creds: pickled credentials

    Returns:
        pd.DataFrame: URL data

    """
    google_sheets_rows = gs.get_google_sheets_rows(google_creds, sheet_range='sold_sheet')
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
        except AttributeError:
            logger.exception(f'Something wrong with row {row}')
            continue
        else:
            if row.sale_price and row.sold:
                update_sale_price(row, db_doc)
                update_sold_date(row, db_doc)
                db_doc['probably_sold'] = False
                logger.info(f'Sale info updated in doc {row.mls_number}')
            if row.notes:
                update_notes(row, db_doc)
                logger.info(f'Notes updated in doc {row.mls_number}')
            support.update_modified_date(db_doc)
            db_doc.save()
        finally:
            sleep(2)


def update_sale_price(row, doc):
    doc['sale_price'] = int(row.sale_price)


def update_sold_date(row, doc):
    sold_date = support.coerce_date_string_to_date(row.sold)
    doc['sold'] = sold_date.strftime(deathpledge.TIMEFORMAT)


def update_notes(row, doc):
    doc['notes'] = row.notes


def refresh_sold_list(google_creds, db_client):
    """Push document list from db back to URL sheet."""
    logger.info('Refreshing Google sheet with view from database')
    sold_view = database.get_view(client=db_client, view='soldList')
    sold_df = create_sold_df_for_gsheet(sold_view)
    sold_list = gs.convert_dataframe_to_list(sold_df)

    # Send to google
    service = build('sheets', 'v4', credentials=google_creds, cache_discovery=False)

    # Clear existing values in all columns
    clear_response = service.spreadsheets().values().clear(
            spreadsheetId=gs.SPREADSHEET_DICT['spreadsheetId'],
            range=gs.SPREADSHEET_DICT['sold_values']
            ).execute()
    logger.info(clear_response)

    data_obj = dict(
        range=gs.SPREADSHEET_DICT['sold_sheet'],
        majorDimension='ROWS',
        values=sold_list)
    data_response = service.spreadsheets().values().batchUpdate(
        spreadsheetId=gs.SPREADSHEET_DICT['spreadsheetId'],
        body=dict(
            valueInputOption='USER_ENTERED',
            includeValuesInResponse=False,
            data=[
                data_obj
            ])
    ).execute()
    logger.info(data_response)


def create_sold_df_for_gsheet(sold_view: dict) -> pd.DataFrame:
    """Create a dataframe from the results of the database view."""
    df = pd.DataFrame.from_dict(
        sold_view, orient='index',
        columns=['added_date', 'mls_number', 'full_address', 'list_price',
            'sale_price', 'sold', 'notes']
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
