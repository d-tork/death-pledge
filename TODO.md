# TODO

* [x] __main__ 70: rename new_homes (they're mostly Active being re-scraped)
* [x] __main__ 88: need to add 'probably_sold' field to raw doc here

* [x] scrape2 84: add log statement if not valid
* [ ] scrape2 126: what if MLS is not in clean? what then?

* [x] database 204: add progress bar to rate limiter

* [ ] bing 379: don't do Bing again if already exists (but it never does exist, because we're
processing the raw right now)

## Manually fix sale prices
1. view: probably_sold (clean) and no sale price or date
2. dump to other google sheet
3. I visit these @ realtor and plug in prices directly to gsheet
4. run separate "refresh sold" module
	1. read gsheet (probably_sold)
	2. open db
	3. for each row:
		if sold price/date not NA
		update CLEAN doc in place
	4. re-pull the probably_sold" view and write over the whole gsheet

# URL View
From raw. DesignDoc = simpleViews

View = urlList (an index). Map function is: 
```java
function (doc) {
  if (doc.doctype === 'home') {
    emit([
      doc.added_date,
      doc.status,
      doc.url,
      doc.mls_number,
      doc.full_address,
      doc._id,
	  doc.probably_sold
    ], 1);
  }
}
```

# 3/25/21

A couple of the probably_sold listings were sent to DB with the two sale prices I had, so I need to loop through all
docs in the DB where probably_sold exists (true or false) and sale price exists, then double-check their values.

Then I need to solve the extension problem so that blank columns are added as well as rows.

## Changes
DCDC510388 - not sold, listed on 1/18/21 for $359,900 and changed to $349,900 on  3/3/21
	- however, that's the MLS from realtor.com which does not match my cloudant: DCDC503778

* [x] DCDC504266 - $395000 on 2/15/21
* [x] VAAR175030 - $295000 on 2/9/21
* [x] VAAR175122 - now listed as a rental
* [x] VAAX255008 - $294000 on 3/5/21
* [x] VAAX255036 - $350000 on 2/19/21
* [x] VAFX1173950 - $384000 on 2/26/21
* [x] VAFX1175916 - $375000 on 2/5/21
* [x] VAFX1176172 - $280000 on 2/19/21
* [x] VAFX1176494 - $352000 on 3/10/21

### First real run
* [x] VAFX1174760
* [x] VAAX255002

### Notes added
VAAR175122 - for rent
DCDC503606 - off market
VAFX1175642 - sold for 289000 (aristotle)

TODO: index the date added field and sort the soldView 
