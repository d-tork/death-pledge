# Cloudant References

## Documentation
IBM Cloudant learning center - http://ibm.biz/cloudant-learning

Cloudant python documentation - https://python-cloudant.readthedocs.io/en/stable/database.html?highlight=bulk#cloudant.database.CouchDatabase.bulk_docs

Python - getting started with Cloudant - https://cloud.ibm.com/docs/services/Cloudant/tutorials?topic=cloudant-getting-started-with-cloudant

Cloudant best and worst practices - https://www.ibm.com/cloud/blog/cloudant-best-and-worst-practices-part-1

## Indices and Querying
[IBM Docs - Cloudant Query](https://developer.ibm.com/clouddataservices/docs/compose/cloudant/cloudant-query/)

[IBM Docs - Indexes](https://developer.ibm.com/clouddataservices/docs/compose/cloudant/indexes/)

[IBM Docs - Using Views](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-using-views)  
- More good videos on the subject: [IBM Cloudant Views](https://developer.ibm.com/clouddataservices/docs/compose/cloudant/views/)

### Design Documents
[IBM Docs - Design Document Management](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-design-document-management)
* stored at `_design/viewname`
* a single design doc can have several views and search indices

### Indices
* an index must exist for a given selector in a query
* you _can_ specify an index at query time, or else Cloudant chooses the index for you

### Options for Querying
1. Primary index
  - `<db url>.com/db/_all_docs`
  - to get all doc IDs
2. Secondary index (aka "view")
  - analytics: counts, sums, averages, etc.
  - uses map-reduce
  - stored in design documents
  - the "key" is the first value emitted, and can be a single field or an array of fields. The key
is what is used to sort and group the index for aggregations.
3. Search index
  - ad-hoc queries on one or more fields
  - searches involving large blocks of text
  - queries that require additional Lucene syntax (wildcards, fuzzy search)
  - stored in design documents
4. Cloudant query
  - if you prefer Mongo-style syntax, for searching with multiple logical operators

### Example Indices 
Full text
```json
{
	"index": {},
	"type": "text"
}
```
Listing status
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

### Example Queries
* If the `fields` key is omitted, the entire document is returned
* The `sort` value must be an array

IDs and house addresses with list price less than or equal to 485,000
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

Recently added houses
```json
{
   "selector": {
      "_id": {
         "$gt": "0"
      },
      "listing.badge": {
         "$in": [
            "For Sale",
            "In Contract"
         ]
      }
   },
   "fields": [
      "_id",
      "added_date",
      "main.full_address",
      "listing.list_price",
      "listing.badge"
   ],
   "sort": [
      {"added_date:string": "desc"}
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
			"$in": ["For Sale", "In Contract"]
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

## Tutorial
Make an index for the Person_dob field (from IMDB example)
```json
{
  "index": {
    "fields": ["Person_dob"]
    },
  "name": "age-index",
  "type": "json"
}
```

Automatically index all fields
```json
{
  "index": {},
  "type": "text"
}
```

**Note**: a query must always have a "selector" in the JSON (as a dict, not an array). This is how
the query is filtered, like for a specific actor or `"movie_year": {$gt": 0}`. However, the
"fields" key (an array) in the JSON determines what is returned in the query. Otherwise I think
all fields in the index are returned. (see [selector syntax](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-query#selector-syntax))
