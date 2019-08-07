import requests
import random
from time import sleep
from fake_useragent import UserAgent


def str_coords(coords):
    str_list = [str(x) for x in coords]
    return ','.join(str_list)


def check_status_of_website(url):
    """Make sure get() returns a 200"""
    ua = UserAgent()
    header = {'User-Agent': str(ua.firefox)}
    result = requests.get(url, headers=header)
    sleep(random.random()*10)
    return result.status_code


def parse_numbers_from_string(s):
    """Get raw numbers from text fields.

    Best to apply this to all the columns in a loop, or perhaps it can be applied to a dataframe?

    Parameters
    ----------
    s.name : pandas Series
        column to be parsed; different columns will require different rules
    """
    if s.name in ['bed', 'bath']:
        func = lambda x: x.split()[0]
    elif s.name == 'sqft':
        func = lambda x: x.split()[0].replace(',', '')
    elif s.name in ['price', 'Price Per SQFT', 'HOA Fee']:
        func = lambda x: x.replace('$', '').replace(',', '')
    elif s.name == 'price-listed':
        func = lambda x: x.split()[2].replace('$', '').replace(',', '')
    # elif s.name == 'Year Built':
    #     func = lambda x: x
    # elif s.name == 'Lot Size Acres':
    #     func = lambda x: x
    else:
        func = lambda x: x  # No transformation applied

    try:
        return s.apply(func, convert_dtype=True)
    except TypeError:
        return s


def clean_columns(df, rename_dict):
    df.rename(columns=rename_dict, inplace=True)
    # TODO: reorder columns
