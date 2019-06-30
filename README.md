# death-pledge

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
## Sources
* https://homescout.homescouting.com/
* https://matrix.brightmls.com/DAE.asp?ID=0-184641887-10


## Documentation
* Bing maps geocode
  * [Find a location by address](https://docs.microsoft.com/en-us/bingmaps/rest-services/locations/find-a-location-by-address#examples)
  * [My apps/keys](https://www.bingmapsportal.com/Application)
  * [Sessions, map control, batch geocoding](https://docs.microsoft.com/en-us/bingmaps/getting-started/bing-maps-api-best-practices)
* [Citymapper API](https://citymapper.3scale.net/)
* [Requests](https://2.python-requests.org/en/master/user/quickstart/)
* [Pipenv](https://docs.pipenv.org/en/latest/install/)
