import pickle
import os.path
import os
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import Code
from Code import support, database

GREEN = dict(red=.34, green=.73, blue=.54)
WHITE = dict(red=1, green=1, blue=1)
RED = dict(red=.90, green=.49, blue=.45)

# Get this file's path
dir_path = os.path.dirname(os.path.realpath(__file__))

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


def get_creds():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cred_file = os.path.join(dir_path, 'google_credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                cred_file, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def get_url_dataframe(google_creds, spreadsheet_dict=SPREADSHEET_DICT, last_n=None, **kwargs):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.

    Args:
        spreadsheet_dict (dict): The spreadsheet object as a dict (parameters, sheets,
            named ranges, etc.).
        last_n (int): Get only last n rows (will trump a force_all parameter).

    Returns:
        DataFrame: Two-column dataframe of URL and date added.

    """
    service = build('sheets', 'v4', credentials=google_creds)
    spreadsheet_id = spreadsheet_dict['spreadsheetId']

    # Call the Sheets API
    print('Getting data from Google sheets...')
    sheet_obj = service.spreadsheets()
    request = sheet_obj.values().get(spreadsheetId=spreadsheet_id, range=spreadsheet_dict['url_range'])
    response = request.execute()
    print('\tdone')

    df = pd.DataFrame.from_records(data=response['values'])
    # Use first row of values as headers
    df = df.rename(columns=df.iloc[0]).drop(df.index[0])
    # Drop null rows
    df.dropna(subset=['url'], inplace=True)

    df_clean = process_url_list(df, **kwargs)
    if last_n:
        return df_clean[-last_n:]
    return df_clean


def process_url_list(df, force_all=False):
    """Make adjustments to URL dataframe before passing as small dataframe.

    Args:
        df (DataFrame): Raw URL dataframe from Google sheets.
        force_all: Keep all URLs, even if status is 'no' or 'Sold'.

    Returns: DataFrame
    """

    def trim_url(url_str):
        """Remove extra params from URL."""
        q_mark = url_str.find('?')
        if q_mark > -1:
            return url_str[:q_mark]
        else:
            return url_str
    df['url'] = df['url'].apply(trim_url)

    if not force_all:
        # drop rows that are Closed (sold)
        df = df.loc[df['status'] != 'Closed']

    return df.copy()


def refresh_url_sheet(creds):
    """Push document list from db back to URL sheet."""

    url_view = database.get_url_list()
    url_df = pd.DataFrame.from_dict(
        url_view, orient='index',
        columns=['added_date', 'status', 'url', 'mls_number', 'full_address', 'docid']
    )
    url_df = url_df.set_index('added_date')
    url_list = prep_dataframe(url_df)

    # Send to google
    service = build('sheets', 'v4', credentials=creds)
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


def prep_dataframe(df):
    """Converts a dataframe to iterable values for Google batchUpdate.

    Returns
        list: data as list of values

    """
    df = df.fillna('').astype('str')
    df = df.reset_index().T.reset_index().T.values.tolist()
    return df


if __name__ == '__main__':
    google_creds = get_creds()
    refresh_url_sheet(google_creds)


