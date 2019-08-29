import pickle
import os.path
import os
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from Code import pandas_handling

GREEN = dict(red=.34, green=.73, blue=.54)
WHITE = dict(red=1, green=1, blue=1)
RED = dict(red=.90, green=.49, blue=.45)

# Get this file's path
dir_path = os.path.dirname(os.path.realpath(__file__))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of my master spreadsheet
SPREADSHEET_DICT = {
    'spreadsheetId': '1ljlZZRXjMb_BEduXqgfc65hQK7cCximT3ebS6UcQPQ0',
    # 'masterlist_range': 'Master_list!A2:AG'
    'url_range': 'URLs',
    'master_range': 'Master_list2!A1',
    'scores': 'Scores!A1'
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
            cred_file = os.path.join(dir_path, 'credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                cred_file, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def get_url_dataframe(google_creds, spreadsheet_dict=SPREADSHEET_DICT):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.

    Parameters
    ----------
    spreadsheet_dict : dict
        The spreadsheet object as a dict (parameters, sheets, named ranges, etc.)

    Returns
    -------
    values_dict : dict
       Data from whole spreadsheet, each key is a month and its values are a list
       of lists, where the inner list is a row of data
    """

    service = build('sheets', 'v4', credentials=google_creds)

    spreadsheet_id = spreadsheet_dict['spreadsheetId']

    # Call the Sheets API
    print('Getting data from Google sheets...')
    sheet_obj = service.spreadsheets()
    request = sheet_obj.values().get(spreadsheetId=spreadsheet_id, range=spreadsheet_dict['url_range'])
    response = request.execute()
    print('Done')

    df = pd.DataFrame.from_records(data=response['values'])
    df = df.rename(columns=df.iloc[0]).drop(df.index[0])
    return df


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
    df_url = df.loc[df['inactive'] == ''][['url', 'date_added']]
    return df_url


def get_url_list():
    """Get list of URLs to scrape from google sheets."""
    my_creds = get_creds()
    df_raw = get_url_dataframe(my_creds)
    return process_url_list(df_raw)


def upload_dataframe(df1, df2, google_creds):
    service = build('sheets', 'v4', credentials=google_creds)
    master_obj = dict(
        range=SPREADSHEET_DICT['master_range'],
        majorDimension='ROWS',
        values=df1)
    scores_obj = dict(
        range=SPREADSHEET_DICT['scores'],
        majorDimension='ROWS',
        values=df2)
    response = service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_DICT['spreadsheetId'],
        body=dict(
            valueInputOption='USER_ENTERED',
            includeValuesInResponse=False,
            data=[
                master_obj,
                scores_obj
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


def upload_data():
    my_creds = get_creds()
    df1, df2 = pandas_handling.merge_data_and_scores()
    df2 = df2.droplevel(0, axis=1)
    df1, df2 = prep_dataframe(df1), prep_dataframe(df2)

    upload_dataframe(df1, df2, my_creds)


def apply_desc_gradient_3(sheet_id, start_col_index, end_col_index, ascending=True):
    if ascending:
        mincolor, maxcolor = RED, GREEN
    else:
        mincolor, maxcolor = GREEN, RED
    grid_range = dict(
        sheetId=sheet_id,
        startRowIndex=1,
        startColumnIndex=start_col_index,
        endColumnIndex=end_col_index)
    gradient_rule = dict(
        minpoint=dict(color=mincolor, type='MIN'),
        midpoint=dict(color=WHITE, type='PERCENTILE', value='50'),
        maxpoint=dict(color=maxcolor, type='MAX'))
    format_rule = {
        'ranges': [grid_range],
        'gradientRule': gradient_rule}
    conditional_format_rule_request = {
        'rule': format_rule,
        'index': 0}
    rule_request = {
        'addConditionalFormatRule': conditional_format_rule_request
    }
    return rule_request


if __name__ == '__main__':
    # sample_url_list = get_url_list()
    upload_data()
    from pprint import pprint

    """Here's how this needs to go: 
    1. first, apply all rules I want (can do this from the web interface)
    2. get response and label the rules by their index number with code comments
    3. change all function calls from add... to updateConditionalFormatting
    4. Any new rules, it must be "add", otherwise, always update
    """
    """
    my_creds = get_creds()
    service = build('sheets', 'v4', credentials=my_creds)
    spreadsheet_id = SPREADSHEET_DICT['spreadsheetId']
    batch_update_spreadsheet_request_body = {
        'requests': [
            # apply_desc_gradient_3(936588282, 35, 36)
        ],
        'includeSpreadsheetInResponse': True
    }
    request = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=batch_update_spreadsheet_request_body)
    response = request.execute()
    pprint(response)
    """
