## References
### Cloudant learning center
http://ibm.biz/cloudant-learning

### Cloudant python documentation
https://python-cloudant.readthedocs.io/en/stable/database.html?highlight=bulk#cloudant.database.CouchDatabase.bulk_docs

### Python - getting started with Cloudant
https://cloud.ibm.com/docs/services/Cloudant/tutorials?topic=cloudant-getting-started-with-cloudant

### Cloudant best and worst practices
https://www.ibm.com/cloud/blog/cloudant-best-and-worst-practices-part-1

## Indices and Querying
### Indices
* an index must exist for a given selector in a query
* you _can_ specify an index at query time, or else Cloudant chooses the index for you

### Full text
```json
{
	"index": {},
	"type": "text"
}
```

### Listing status
```json
{
	"index": {
		"fields": {
			"listing.badge": "asc"
		},
		"partial_filter_selector": {
			"$or": [
				"For Sale",
				"In Contract"
			]
		}
	},
	"name":"listingByStatus",
	"type":"json"
}
```

## Queries
* If the `fields` key is omitted, the entire document is returned
* The `sort` value must be an array

### IDs and house addresses with list price less than or equal to 485,000
```json
{
	"selector": {
		"_id": {
			"$gt": "0"
		},
			"listing.list_price": {
				"$lte": 485000
			}
	},
		"fields": [
			"_id",
			"_rev",
			"main.full_address",
			"listing.list_price"
		],
		"sort": [
      {
				"_id": "asc"
      }
   ]
}
```

### Search within text
```json
{
	"selector": {
		"main.full_address": {"$regex": "4501 ARLINGTON"}
	},
	"fields": [
		"_id", "main.full_address"
	]
}
```

### Active listings
```json
{
	"selector": {
		"listing.badge": {
			"$in": [
				"For Sale",
				"In Contract"
			]
		}
	},
	"fields": [
		"_id",
		"main.full_address",
		"listing.list_price"
	],
	"use_index": "listingByStatus"
}
```

### Specifying an index to use
```json
{
    "use_index": "_design/7bf95044..."
}
```

## Multi-document fetching
* use a `POST` request in the form of a query of a view, passing the following
content as the data: 
	```json
	{
		"keys": [
			"key1",
			"key2"
		]
	}
	```

* This is more efficient than using multiple `GET` API requests.
* However, don't just use `include_docs=true` to get the data back; instead, 
specify what data should be returned in the design document via `emit`, and those
fields will be retrieved directly from the view index file, not the database.

