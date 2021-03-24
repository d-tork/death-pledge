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

