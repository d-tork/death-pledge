from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup


def simple_get(url):
    """
    Attempts to get the content at 'url' by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        log_error('Error during requests to {0} : {1}'.format(url, str(e)))
        return None


def is_good_response(resp):
    """
    Returns True if the response seems to be HTML, False otherswise.
    """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(e):
    print(e)


def get_names():
    """
    Downloads the page where the list of mathematicians is found
    and returns a list of strings, one per mathematician
    :return:
    """
    url = 'http://www.fabpedigree.com/james/mathmen.htm'
    response = simple_get(url)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        names = set()
        for li in html.select('li'):
            for name in li.text.split('\n'):
                if len(name) > 0:
                    names.add(name.strip())
        return list(names)

    # Raise exception if we failed to get any data from the url
    raise Exception('Error retrieving contents at {}'.format(url))


def get_house_data(url):
    """Get onesheet for a specific listing"""
    response = simple_get(url)

    if response is not None:
        html = BeautifulSoup(response, 'html.parser')
        garagedivs = html.findAll('div', {'class': 'feature-group-name'})
        for div in garagedivs:
            print(div)
        return

    raise Exception ('Error retrieving contents from url.')

if __name__ == "__main__":
    listing_url = r"https://homescout.homescouting.com/detail?HasOpenHouse=false&MLSListingID=VAAR100626&TeamId=7196788&VipCodeId&l=36003518&q=921835"
    soup = get_house_data(listing_url)
