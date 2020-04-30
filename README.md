# death-pledge
From Anglo-Norman _morgage_, Middle French _mortgage_, from Old French _mort gage_ ("death pledge"), after a 
translation of judicial Medieval Latin _mortuum vadium_ or _mortuum wadium_. So called because the deal dies either
when the debt is paid or when payment fails.

## Installation
Clone this repo, make sure you have [pipenv](https://docs.pipenv.org/en/latest/) installed, then run
```
$ cd death-pledge
$ pipenv install
```
This should install all dependencies needed, and you're ready to run a module. Start a subshell within your virtual 
environment like so:
```
$ pipenv shell
```
Or run things without explicitly activating the virtual environment: 
```
$ pipenv run python citymapper.py
```

### with `virtualenv`

A requirements.txt file is included for use with `venv`, for my dumb Raspberry Pi that couldn't handle `pipenv`.

Also be sure to have the linux version of `geckodriver` and an appropriate version of Firefox, with the Selenium version to match.

```
$ source venv/bin/activate
$ pip install -r requirements.txt
$ pip install .
```

## Usage
Only with the proper credentials can this be run:
* Google OAuth for my spreadsheet, or else feed it your own list of URLs
* Real estate login
* Bing Maps API token
* Citymapper token

1. Run `main.py`, after checking which of the two functions is active. Or, 
2. Run a specific function from the command line: 
```
$ python -c 'from Code import main; main.single_sample()'
```

## Sources
* https://homescout.homescouting.com/
* https://matrix.brightmls.com/DAE.asp?ID=0-184641887-10


## Documentation
* Bing maps geocode
  * [Find a location by address](https://docs.microsoft.com/en-us/bingmaps/rest-services/locations/find-a-location-by-address#examples)
  * [My apps/keys](https://www.bingmapsportal.com/Application)
  * [Sessions, map control, batch geocoding](https://docs.microsoft.com/en-us/bingmaps/getting-started/bing-maps-api-best-practices)
  * [More options with Bing](https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/)
    * likely to replace Citymapper with Bing, since the CM API is failing me and times are wildly inconsistent.
* [Citymapper API](https://citymapper.3scale.net/)
* [Requests](https://2.python-requests.org/en/master/user/quickstart/)
* [Pipenv](https://docs.pipenv.org/en/latest/install/)
* gspread
  * [Write data back to Google sheets](https://github.com/burnash/gspread#authorization-using-oauth2)
* Google sheets API
  * https://developers.google.com/sheets/api/
