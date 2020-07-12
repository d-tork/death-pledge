# Documentation

## Additional Measures

### Neighborhood
* [ ] crime
* [ ] school distances
* [ ] bus stops
* [ ] median income
* [ ] median age
* [ ] owner-occupied vs. rented
* [ ] education

## Data sources
### Bing Maps
* [Find a location by address](https://docs.microsoft.com/en-us/bingmaps/rest-services/locations/find-a-location-by-address#examples)
* [My apps/keys](https://www.bingmapsportal.com/Application)
* [Sessions, map control, batch geocoding](https://docs.microsoft.com/en-us/bingmaps/getting-started/bing-maps-api-best-practices)
* [More options with Bing](https://docs.microsoft.com/en-us/bingmaps/rest-services/routes/)
	* likely to replace Citymapper with Bing, since the CM API is failing me and times are wildly inconsistent.

### Citymapper maps
* [Citymapper API](https://citymapper.3scale.net/)

### Data.gov
https://catalog.data.gov/group/finance3432#topic=finance_navigation
* housing and communities


### Kaggle
https://www.kaggle.com/c/house-prices-advanced-regression-techniques/data
* predicting sale price with machine learning

### Airbnb
Room rent prices, vacancies

### City/county assessor
**Fairfax County:** https://icare.fairfaxcounty.gov/ffxcare/search/commonsearch.aspx?mode=address
- Franconia
- Huntington
- Kingstowne
- Lincolnia
- Merrifield
- Pimmit Hills
- Tysons

**Prince George's County:** http://sdat.dat.maryland.gov/RealProperty/Pages/default.aspx

**Alexandria:** https://realestate.alexandriava.gov/index.php?action=address

**Arlington County:** https://propertysearch.arlingtonva.us/Home/Search

**Falls Church:** http://property.fallschurchva.gov/Parcelviewer/

### Crime stats
* not just violent crimes, but 311 non-emergency complaints, street & sidewalk cleaning, property damage, graffiti, street defects
* Arlington County
	- [Incident tracking](https://police.arlingtonva.us/incident-tracking/) - download a bunch of files, enrich them with geocoords, add to elasticsearch index for map overlay
* Alexandria
	- [Crime Database Search](https://apps.alexandriava.gov/CrimeReport/Result.aspx?&sd=20190506&ed=20200513) - will need to scrape and parse, possibly browsing through pages. Should be an easy requests or BS4 project though.
	- [SpotCrime Crime Blotter](https://spotcrime.com/va/alexandria/daily) - individual pages with tabulated data, requires scraping and parsing

### Income & poverty, homelessness

## Development tools
### Cloudant
see [Cloudant docs](cloudant.md)

### RPI3
* https://stackoverflow.com/questions/52534658/webdriverexception-message-invalid-argument-cant-kill-an-exited-process-with
* Get the latest [_linux_ release](https://github.com/mozilla/geckodriver/releases) of geckodriver as well
* **new** (12 Jul): containerize it, then it should run just fine

### Google sheets
* Google sheets API
  * https://developers.google.com/sheets/api/
* [gspread: Write data back to Google sheets](https://github.com/burnash/gspread#authorization-using-oauth2)
