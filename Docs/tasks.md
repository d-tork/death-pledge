HOUSE HUNTING MODULE

1. Get to where I can plug in an address and get back the walk score
2. Scrape the important stuff: 
	-URL
	-address
	-city, state
	-price
	-square footage
	-bedrooms, bathrooms
	-year built
3. ~Get commute time from citymapper (at specific times)~
4. Stats on neighborhood: crime, school distances, bus stops(?), median income, median age, gender breakdown, education
5. Need to have a pre-evaluation score (based on pure stats/numbers scraped), and a post-evaluation score (after I've been able to look through photos closely, or else visit myself)
6. Export in format that can be dragged into Google Maps
	with clusters! And ratings!
7. Write lat/lon coordinates and full address w/ zip back to google sheets (saves me on the API calls)


More difficult: 
1. parking
2. washer/dryer
3. rating the kitchen, bedrooms, bathrooms, neighborhood, backyard

# Coding TODOs:
1. find a way to rename the two different status fields (right now it's just the difference of a capital letter)
2. ~~parse out the `price-listed` field (it still has text in it, unless of course that text changes to "sold price" or whatever. That might be useful.~~
  * meh, it's kinda useful to see it on sold properties
  * parse them anyway, then make a `sale-price-diff` column
3. ~~parse numbers from `sqft` field~~
4. ~~parse numbers from `Price Per SQFT`~~
  * ~~now it's occurring to me: I should group the attributes by what kind of parsing or checking that needs to be done on them, not some arbitrary meta/details/whatever~~
5. ~~parse numbers from bed and bath~~
6. ~~When running main.py, check if URL already has data. If so, only update price and status (basic fields). Save me a lot of time.~~ Eventually, I want to be reading _and_writing to a google sheet

## Rate the existing attributes I scraped:
1. Like `Has HOA`, `HOA Fee` (only if it has it), `Waterfront YN`, `Has Basement`, etc. 
* I'm thinking since this attribute dataframe is so large, I need to make a separate one which assigns scores to all these attributes. THEN, I add up the _weighted_ scores to get a total score.
