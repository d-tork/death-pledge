import pickle
import os.path
import os
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import deathpledge
from deathpledge import support, database

GREEN = dict(red=.34, green=.73, blue=.54)
WHITE = dict(red=1, green=1, blue=1)
RED = dict(red=.90, green=.49, blue=.45)

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


def get_creds(token_path=TOKENPATH):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
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


def get_url_dataframe(google_creds, spreadsheet_dict=SPREADSHEET_DICT, last_n=None, **kwargs):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.

    Args:
        google_creds: pickled (?) credentials
        spreadsheet_dict (dict): The spreadsheet object as a dict (parameters, sheets,
            named ranges, etc.).
        last_n (int): Get only last n rows

    Returns:
        DataFrame: Two-column dataframe of URL and date added.

    """

    def trim_url(url_str):
        """Remove extra params from URL."""
        q_mark = url_str.find('?')
        if q_mark > -1:
            return url_str[:q_mark]
        else:
            return url_str

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

    # Remove junk from URLs
    df['url'] = df['url'].apply(trim_url)

    if last_n:
        return df[-last_n:]
    return df


def refresh_url_sheet(creds):
    """Push document list from db back to URL sheet."""

    url_view = database.get_url_list()
    url_df = pd.DataFrame.from_dict(
        url_view, orient='index',
        columns=['added_date', 'status', 'url', 'mls_number', 'full_address', 'docid']
    )
    url_df['added_date'] = pd.to_datetime(url_df['added_date']).dt.strftime('%m/%d/%Y')
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
    sample_creds = get_creds()
    print(get_url_dataframe(sample_creds))
    refresh_url_sheet(sample_creds)


