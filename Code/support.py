import requests
import random
import datetime as dt
from time import sleep
from fake_useragent import UserAgent


class BadResponse(Exception):
    pass


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


def get_commute_datetime(mode, dayofweek=1, hrmin='06:30'):
    """Get my work commute time for the next day specified.
    By default, work time is 06:30 and day is Tuesday.

    Adapted from SO 6558535

    Args:
        mode (str): {'cm', 'bing'}
            determines the format for citymapper or bing
        dayofweek (int): index of weekday, default 1 (Tuesday)
            0=Mon, 1=Tue, 2=Wed, 3=Thur, 4=Fri, 5=Sat, 6=Sun
        hrmin (str): 24-hour specifying departure or arrival time, default 6:30 AM
            Departure if driving, arrival time if transit

    :return: str formatted as datetime for given mode
    """
    now = dt.datetime.now()
    days_ahead = dayofweek - now.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    wday = now + dt.timedelta(days_ahead)
    wtime = dt.datetime.strptime(hrmin, '%H:%M').time()
    work_datetime = dt.datetime(wday.year, wday.month, wday.day, wtime.hour, wtime.minute)

    # Format for mode
    if mode == 'cm':
        return '{}-0400'.format(work_datetime.isoformat())
    elif mode == 'bing':
        # dateTime=03/01/2011 05:42:00
        return work_datetime.strftime('%m/%d/%Y %H:%M:%S')


def str_time_to_min(s):
    """Converts a HH:MM:SS string to decimal minutes."""
    try:
        dur = dt.datetime.strptime(s.split()[0], '%H:%M:%S')
    except (TypeError, ValueError):
        return None
    delta = dt.timedelta(hours=dur.hour, minutes=dur.minute, seconds=dur.second)
    return delta.total_seconds()/60


def clean_columns(df, rename_dict):
    df.rename(columns=rename_dict, inplace=True)
    # TODO: reorder columns
