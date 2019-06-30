import pickle
import os.path
import os
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Get this file's path
dir_path = os.path.dirname(os.path.realpath(__file__))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of my master spreadsheet
SPREADSHEET_DICT = {
    'spreadsheetId': '1ljlZZRXjMb_BEduXqgfc65hQK7cCximT3ebS6UcQPQ0',
    'range': 'Master_list!A2:AG'
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



def main(google_creds, spreadsheet_dict):
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
    sheet_obj = service.spreadsheets()
    request = sheet_obj.values().get(spreadsheetId=spreadsheet_id, range=spreadsheet_dict['range'])
    response = request.execute()

    df = pd.DataFrame.from_records(data=response['values'])
    df = df.rename(columns=df.iloc[0]).drop(df.index[0])
    return df

if __name__ == '__main__':
    MY_CREDS = get_creds()
    df_raw = main(MY_CREDS, SPREADSHEET_DICT)
