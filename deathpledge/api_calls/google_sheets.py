import pickle
import os.path
import os
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import deathpledge
from deathpledge import support, database

# Get this file's path
DIRPATH = os.path.dirname(os.path.realpath(__file__))
TOKENPATH = os.path.join(DIRPATH, 'token.pickle')

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


class URLDataFrame(object):
    """Stores the URLs from Google, acts mostly like a Pandas DataFrame.

    Args:
        df (pd.DataFrame): data being passed
        force_all (bool): Whether to scrape all listings from the web, or
            scrape only active ones and fetch the rest from the database
        last_n (int): Get only last n rows (optional, else returns all)

    """
    def __init__(self, df, force_all=False, last_n=None):
        self.df = df
        self.force_all = force_all
        self.last_n = last_n

        self.rows_to_scrape = pd.DataFrame()
        self.rows_not_to_scrape = pd.DataFrame()

        self.prepare_dataframe()
        self.trim_last_n()
        self.split_scrape_from_noscrape()

        if self.force_all:
            self.rows_to_scrape = self.df
        else:
            self.split_scrape_from_noscrape()

    def __getattr__(self, attr):
        return getattr(self.df, attr)

    def prepare_dataframe(self):
        self.set_first_row_as_headers()
        self.drop_null_rows()
        self.remove_junk_from_urls()

    def set_first_row_as_headers(self):
        self.df = self.df.rename(columns=self.df.iloc[0]).drop(self.df.index[0])

    def drop_null_rows(self):
        self.df.dropna(subset=['url'], inplace=True)

    def remove_junk_from_urls(self):
        self.df['url'] = self.df['url'].apply(self.trim_url)

    @staticmethod
    def trim_url(url_str):
        """Remove extra params from URL."""
        q_mark_location = url_str.find('?')
        if q_mark_location > -1:
            return url_str[:q_mark_location]
        else:
            return url_str

    def trim_last_n(self):
        if self.last_n:
            self.df = self.df[-self.last_n:]

    def split_scrape_from_noscrape(self):
        self.rows_to_scrape = self.df.loc[self.df['status'] != 'Closed'].copy()
        self.rows_not_to_scrape = self.df.loc[self.df['status'] == 'Closed'].copy()


def get_creds(token_path=TOKENPATH):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = get_existing_token(token_path)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(f'DIRPATH IS: {DIRPATH}')
            cred_file = os.path.join(DIRPATH, 'google_credentials.json')
            print(f'cred_file IS: {cred_file}')
            flow = InstalledAppFlow.from_client_secrets_file(
                cred_file, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def get_existing_token(token_path):
    with open(token_path, 'rb') as token_file:
        token = pickle.load(token_file)
    return token


def get_url_dataframe(google_creds, **kwargs):
    """Get manually curated list of realscout URLs from Google sheets.

    Args:
        google_creds: pickled credentials
        last_n (int): Get only last n rows (optional, else returns all)

    Returns:
        DataFrame: URL data

    """
    google_sheets_rows = get_google_sheets_rows(google_creds)
    google_df = URLDataFrame(
        pd.DataFrame.from_records(data=google_sheets_rows),
        **kwargs
    )

    return google_df


def get_google_sheets_rows(google_creds):
    print('Getting data from Google sheets...')
    response = get_google_sheets_api_response(google_creds)
    rows = get_values_from_google_sheets_response(response)
    print('\tdone')
    return rows


def get_google_sheets_api_response(google_creds):
    service = build('sheets', 'v4', credentials=google_creds)
    sheet_obj = service.spreadsheets()
    request = sheet_obj.values().get(spreadsheetId=SPREADSHEET_DICT['spreadsheetId'],
                                     range=SPREADSHEET_DICT['url_range'])
    response = request.execute()
    return response


def get_values_from_google_sheets_response(response):
    return response['values']


def refresh_url_sheet(google_creds):
    """Push document list from db back to URL sheet."""

    url_view = database.get_url_list()
    url_df = pd.DataFrame.from_dict(
        url_view, orient='index',
        columns=['added_date', 'status', 'url', 'mls_number', 'full_address', 'docid']
    )
    url_df['added_date'] = pd.to_datetime(url_df['added_date']).dt.strftime('%m/%d/%Y')
    url_df = url_df.set_index('added_date')
    url_list = prep_dataframe_to_update_google(url_df)

    # Send to google
    service = build('sheets', 'v4', credentials=google_creds)
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
    print(response)


def prep_dataframe_to_update_google(df):
    """Converts a dataframe to iterable values for Google batchUpdate.

    Returns
        list: data as list of values

    """
    df = df.fillna('').astype('str')
    df = df.reset_index().T.reset_index().T.values.tolist()
    return df


if __name__ == '__main__':
    sample_creds = get_creds()
    sample_urls = get_url_dataframe(sample_creds)
    print(sample_urls.head())
    refresh_url_sheet(sample_creds)


