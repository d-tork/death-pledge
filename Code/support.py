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


def clean_columns(df, rename_dict):
    df.rename(columns=rename_dict, inplace=True)
    # TODO: reorder columns
