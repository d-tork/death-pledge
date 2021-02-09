import pickle
import os
import logging
import pandas as pd
import numpy as np
from urllib.parse import urlparse, urlunparse
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.auth.exceptions import TransportError

from deathpledge import database

logger = logging.getLogger(__name__)

# Get this file's path
DIRPATH = os.path.dirname(os.path.realpath(__file__))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of my master spreadsheet
SPREADSHEET_DICT = {
    'spreadsheetId': '1ljlZZRXjMb_BEduXqgfc65hQK7cCximT3ebS6UcQPQ0',
    # 'masterlist_range': 'Master_list!A2:AG'
    'url_range': 'URLs',
    'master_range': 'Master_list!A1',
    'scores': 'Scores!A1',
    'raw_data': 'raw_data!A1'
}


class CredsNotValidError(Exception):
    """Credentials are invalid or expired."""
    pass


class URLDataFrame(object):
    """Stores the URLs from Google, acts mostly like a Pandas DataFrame.

    Args:
        df (pd.DataFrame): data being passed
        last_n (int, Optional): Get only last n rows. Defaults to None.

    """
    def __init__(self, df, last_n=None):
        self.df = df
        self._prepare_dataframe()
        if last_n is not None:
            self._trim_last_n(last_n)
        self._set_order_newest_to_oldest()

    def __getattr__(self, attr):
        return getattr(self.df, attr)

    def _prepare_dataframe(self):
        self._set_first_row_as_headers()
        self._drop_null_rows()
        self._remove_duplicate_listings()
        self._fill_blanks_with_na()

    def _set_first_row_as_headers(self):
        self.df = self.df.rename(columns=self.df.iloc[0]).drop(self.df.index[0])

    def _drop_null_rows(self):
        self.df.dropna(subset=['url'], inplace=True)

    def _remove_duplicate_listings(self):
        self.df.drop_duplicates(subset=['url'], keep='first', inplace=True)

    def _fill_blanks_with_na(self):
        self.df.replace('', np.nan, inplace=True)

    def _set_order_newest_to_oldest(self):
        self.df.sort_index(ascending=False, inplace=True)

    def _trim_last_n(self, n):
        self.df = self.df[-n:]

    def drop_closed_listings(self):
        closed = self.df.loc[self.df['status'].str.lower().isin(['closed', 'expired'])]
        self.df = self.df.drop(index=closed.index)


class GoogleCreds(object):
    """Credentials for OAuth2.

    The file token.pickle stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first
    time.

    Attributes:
        creds_dict: OAuth2 credentials.

    """

    def __init__(self, creds_dict, creds_path=None):
        """Load credentials or generate them if they don't exist.

        Args:
            creds_dict (dict): Keys loaded from deathpledge config
            creds_path (str, Optional): Path to credentials if token is invalid.

        """
        self.creds_path = creds_path
        self.creds_dict = creds_dict
        self.creds = self._get_valid_creds()

    def _get_valid_creds(self):
        """Load, refresh, or get new creds as needed."""
        creds = self._get_new_creds()
        return creds

    def _get_new_creds(self):
        """Request new token with creds supplied."""
        try:
            creds = service_account.Credentials.from_service_account_info(self.creds_dict)
        except:
            creds = service_account.Credentials.from_service_account_file(self.creds_path)
        return creds


def get_url_dataframe(google_creds, **kwargs):
    """Get manually curated list of realscout URLs from Google sheets.

    Args:
        google_creds: pickled credentials
        **kwargs: passed to URLDataFrame instance

    Returns:
        DataFrame: URL data

    """
    google_sheets_rows = get_google_sheets_rows(google_creds)
    google_df = URLDataFrame(
        pd.DataFrame.from_records(data=google_sheets_rows),
        **kwargs
    )
    google_df.drop_closed_listings()
    return google_df


def get_google_sheets_rows(google_creds):
    logger.info('Getting data from Google sheets')
    response = get_google_sheets_api_response(google_creds)
    rows = get_values_from_google_sheets_response(response)
    return rows


def get_google_sheets_api_response(google_creds):
    service = build('sheets', 'v4', credentials=google_creds, cache_discovery=False)
    sheet_obj = service.spreadsheets()
    request = sheet_obj.values().get(spreadsheetId=SPREADSHEET_DICT['spreadsheetId'],
                                     range=SPREADSHEET_DICT['url_range'])
    response = request.execute()
    return response


def get_values_from_google_sheets_response(response):
    return response['values']


def refresh_url_sheet(google_creds, db_client):
    """Push document list from db back to URL sheet."""
    logger.info('Refreshing Google sheet with view from raw database')
    url_view = database.get_url_list(client=db_client)
    url_df = pd.DataFrame.from_dict(
        url_view, orient='index',
        columns=['added_date', 'status', 'url', 'mls_number', 'full_address', 'docid']
    )
    url_df['added_date'] = pd.to_datetime(url_df['added_date']).dt.strftime('%m/%d/%Y')
    url_df.dropna(subset=['added_date'], inplace=True)
    url_df = url_df.set_index('added_date')
    url_list = prep_dataframe_to_update_google(url_df)

    # Send to google
    service = build('sheets', 'v4', credentials=google_creds, cache_discovery=False)
    url_obj = dict(
        range=SPREADSHEET_DICT['url_range'],
        majorDimension='ROWS',
        values=url_list)
    response = service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_DICT['spreadsheetId'],
        body=dict(
            valueInputOption='USER_ENTERED',
            includeValuesInResponse=False,
            data=[
                url_obj
            ])
    ).execute()
    logger.info(response)


def prep_dataframe_to_update_google(df):
    """Converts a dataframe to iterable values for Google batchUpdate.

    Returns
        list: data as list of values

    """
    df = df.fillna('').astype('str')
    df = df.reset_index().T.reset_index().T.values.tolist()
    return df


def test_refresh():
    import deathpledge
    google_creds = GoogleCreds(
        creds_dict=deathpledge.keys.get('Google_creds')
    ).creds

    with database.DatabaseClient() as cloudant:
            refresh_url_sheet(google_creds, db_client=cloudant)