In main.py, create functions I will frequently want to run on all the listings:
scrape all URLs
re-scrape all on-market JSONs
supplement all (rename modify.py to supplement, or something like that)
score all
pull from google (checks for any new information)
push all to google (pushing scores and some listing info...not the individual bed/bath counts, but the important info)
	-here's where we practice a little opsec.


Batch update: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate
Conditional formatting: https://developers.google.com/sheets/api/samples/conditional-formatting


# TODO: 
- [x] rename 'change_from_initial' to 'change', then 'pct_change'
- [ ] score the % change from initial price? 
- [x] move 'sold' date to before 'sale_price'
- [x] move 'sold', 'sale_price', and 'sale_diff_pct' to end of dataframe
- [x] add % diff between tax assessed value and current price
    - [ ] and score it
- [ ] ensure that any nulls are filled with blank space, not with numbers!
- [ ] consider rearranging the scorecard dicts (continuous first)
    - [ ] then within that change, place price, commute, and bus stop first before others so they appear to the left of the spreadsheet
- [ ] push scores dataframe to new spreadsheet to share with DB
- [ ] update Blacksnake (and find a way to make those kinds of manual changes permanent!)
    - One way to handle this (and the visitation scoring mentioned below) is to have two more sheets in the Google spreadsheet: one for initial impression, one for post-visit impression. Python can write the index to the google sheet (MLS, URL, address, total score) and the rest of the columns will be created in google with fields for me to score (modernity, kitchen, bedrooms, living spaces, yard(s), etc.). So the index will automatically be populated with new houses. The only issue is keeping them aligned with the correct rows (when it writes a new list of houses, sorted by score, it will end up shifting houses away from their original rows and therefore away from their assessments). What must happen is 1) read the whole sheet as a dataframe, 2) make MLS the index, 3) add new houses (reindex?), then 4) sort and write the whole thing back to Google.
- [ ] **IDEA:** get raspberry pi up and running again, clone the repo, then set it to run the whole script on command. That command can be sent from my phone on a lunch break.
    - research headless mode (https://www.raspberrypi.org/documentation/configuration/wireless/headless.md)
    - need to prevent it from sleeping so VNC can connect (https://stackoverflow.com/questions/30985964/how-to-disable-sleeping-on-raspberry-pi)
- [ ] metro walk score should probably be weighted a little bit higher than commute score (or at least higher than it is now), because metro walk is applicable to everyone (not just me) and at all times (not just early morning), and my commute will feasibly change (maybe even to a driving commute in the opposite direction, like Belvoir or McLean) yet the metro walk will still be valuable.
- [ ] price and price per sqft definitely need to be weighted higher, or else commute's weight be reduced. See: the DC property for $550K that made it in the top 10 despite being the most expensive house I've analyzed AND in D.C.
- [x] Can I store JSONs in google drive? That's the only way to access them here
    - [ ] share the new folder (from Excel Help to me), then access that shared folder via my own drive on computer. Set up a bash script to rsync every morning while I'm on my way to work.
    - bash script and cron job did not run this morning. I think I need to add the cron job or activate it or something, even though it's in the launcher folder. 
- [ ] add summary statistic of local travel driving times
    - [ ] score continuously each drive time (with minimum 5 min and max 45, descending), then divide each of those scores by the total number of trips so that the whole thing added up will be a "local driving" score on a scale of 0 to 3.5. Weighted by a factor of 1 or 2, of course. Store it in quickstats, or local travel?
- [ ] create visitation sheet in google with the fields that I would rate in person. Then read that sheet it, condense it down to a single number or two, and factor it into the scorecard. It can (and often should) be negative, as this is an adjustment of my first impression. Internal to this manual assessment is a weighting scheme, where the neighborhood and modernity threshold should be weighted quite heavily (considering there's not much information available to to me on those things prior to the visit). 
- [ ] get and score the availability of grocery stores and department stores. Should be weighted pretty low (considering I can resume a normal person's grocery shopping habits I suppose). 
- [ ] add a verdict field where I can say yay or nay and overrule the total score ranking and the sold badge (essentially it would become inactive even when not sold. _Ideally_ I would find where the ranking went wrong, but sometimes it's as simple as I hate everything about the layout of the house, but that can't be represented in data avilable to me.
    - the question then becomes: how do I deal with those no's properly? Removed from the list? Score reduced to zero? Or just greyed out and left out of the "active" filter view?
- [ ] add JBAB to local driving (to balance out Myer and Belvoir)
- [ ] consider, instead of bus walk distance (although I really like that measure), it should be the walk distance for the first leg of the trip regardless of what the destination is. Because a few of these listings are getting by with 0-min bus stop walks simply because the first leg of the trip isn't to a bus stop, it's straight to the metro. However, that walk is 20-30 minutes and if that's the reality of the daily commute (30 min walking, 5 min metro ride) then that's a bit of a problem. 

## Google Sheets REST API for getting response without requests
Use HTTP request:  
```
GET https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}?ranges=Scores!A1:I65&fields=sheets.conditionalFormats
```
But with more parameters, like so:

```python
params = {
    'spreadsheetId': '1ljlZZRXjMb_BEduXqgfc65hQK7cCximT3ebS6UcQPQ0',
    'ranges': 'Scores!A1:I65',
    'prettyPrint': True,
    'fields': 'sheets.conditionalFormats'  # for multiple fields, should it be a list? Or just comma-separated string?
    }

# from the video
rsp = SHEETS.spreadsheets().get(spreadsheetId=sheetID,
    fields='sheets.conditionalFormats'
).execute()

```

**New!** How to format the request!:  
https://developers.google.com/sheets/api/guides/concepts  
How to clear the values from a range in batchUpdate:  
https://developers.google.com/sheets/api/samples/sheet

