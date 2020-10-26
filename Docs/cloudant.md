# Cloudant References

## References
IBM Cloudant learning center - http://ibm.biz/cloudant-learning

Cloudant python documentation - https://python-cloudant.readthedocs.io/en/stable/database.html?highlight=bulk#cloudant.database.CouchDatabase.bulk_docs

Python - getting started with Cloudant - https://cloud.ibm.com/docs/services/Cloudant/tutorials?topic=cloudant-getting-started-with-cloudant

Cloudant best and worst practices - https://www.ibm.com/cloud/blog/cloudant-best-and-worst-practices-part-1

[IBM Docs - Using Views](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-using-views)  

[IBM Cloudant Learning Center Youtube playlist](https://www.youtube.com/playlist?list=PLJa_sXrJUZb8FouDUo1KvZujd_icgaejg)

[Tutorials by a real human](https://sharynr.github.io/ibm-cloudant-lab/index.html)

## Authentication
* [Identity and Access Management](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-ibm-cloud-identity-and-access-management-iam-)
* [Cloudant authentication](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-authentication)
* Service-level credentials vs. [IBM Cloud personal API key](https://cloud.ibm.com/docs/account?topic=account-userapikey#create_user_key) 
* IAM access token is included in the `Authorization` HTTP header to the service.

With Python:
```python
from cloudant.client import Cloudant
client = Cloudant.iam(
    "76838001-b883-444d-90d0-46f89e942a15-bluemix",
    "MxVp86XHkU82Wc97tdvDF8qM8B0Xdit2RqR1mGfVXPWz",
    connect=True
)
print(client.all_dbs())
```

With HTTP:
```
curl "https://iam.cloud.ibm.com/identity/token" \
    -k -X POST \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --header "Accept: application/json" \
    --data-urlencode "grant_type=urn:ibm:params:oauth:grant-type:apikey" \
    --data-urlencode "apikey=$apikey"
```

### HTTP request methods
* `GET`: request specified items, i.e. database docs
* `POST`: upload data, i.e. to set values, upload documents, start administration commands
* `PUT`: "store" a specific resource, i.e. create new objects including databases, documents, views, and design docs

## Design Documents
[IBM Docs - Design Document Management](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-design-document-management)
* stored at `_design/viewname`
* a single design doc can have several views and search indices
* indexes can be grouped into design docs for efficiency, or else they are created in their own ddoc (by dfault).
You can specify which one in the JSON as `ddoc`.

## Indices
[IBM Docs - Indexes](https://developer.ibm.com/clouddataservices/docs/compose/cloudant/indexes/)

* an index must exist for a given selector in a query
* you _can_ specify an index at query time, or else Cloudant chooses the index for you
    * **HOW does it choose?** To identify which index is being used by a particular query, send a POST to the
    `_explain` endpoint for the database with the query as data.
* can be one of two types: `json` (default) or `text`
    * `json`: if you know exactly what data you want to look for; you specify how the index is created
    * `text`: maximum search flexibility; automatically indexes all fields in the docs

### [Partial indexes](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-query#creating-a-partial-index)
If you only need to index a subset of a database then a partial index can make the index smaller and more efficient by 
applying a filter _selector* at indexing time. A similar effect is achieved with an `if` statement in a MapReduce or 
Search index:

```javascript
function(doc) {
    // we only want totals of paid orders
    if (doc.type === 'order' && doc.status == 'paid') {
        //build in index of order value by date, but only for paid-for orders
        emit(doc.date, doc.total)
    }
}
```

Without partial indexes, a query like 
```json
{
  "selector": {
    "status": {
      "$ne": "archived"
    },
    "type": "user"
  }
}
```
will require a full index scan to find all the documents of `type`:`user` that don't have a status of `archived`. To
improve response time, create the partial index: 
```json
{
  "index": {
    "partial_filter_selector": {
        "status": {
          "$ne": "archived"
        }
    },
    "fields": ["type"]
    },
  "ddoc": "type-not-archived",
  "type": "json"
}
```

### Example Indices 
Full text
```json
{
	"index": {},
	"type": "text"
}
```
This is lazy though. Consider adding a `fields` array to limit searches to only the fields required
 by your queries.
 
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
* `fields` array: if you know an index queries only on specific fields, then this can be used to limit the size of the
index. Each field must also specify a type to be indexed. Acceptable tyeps are `boolean`, `string`, and `number`

## Query
[IBM Docs - Cloudant Query](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-query)

**Note**: a query must always have a "selector" in the JSON (as a dict, not an array). This is how
the query is filtered, like for a specific actor or `"movie_year": {$gt": 0}`. However, the
"fields" key (an array) in the JSON determines what is returned in the query (like Elasticsearch `_source`). Otherwise
all fields in the index are returned. (see [selector syntax](https://cloud.ibm.com/docs/Cloudant?topic=Cloudant-query#selector-syntax))

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

### Example Queries
* If the `fields` key is omitted, the entire document is returned
* The `sort` value must be an array

Plain text query (for the full text index above):
```json
{
  "selector": {
    "$text": "Bond"
  }
}
```

When an explicit operator is not given (`$eq`, `$gt`, `$gte`, `$lt`, `$lte`, `$ne`), `$eq` is implied,
```json
{
  "selector": {
    "director": "Lars von Trier"
  }
}
```
is equivalent to
```json
{
  "selector": {
    "director": {
      "$eq": "Lars von Trier"
    }
  }
}
```

Here's how `OR` criteria would be written (I think, they left out the "selector" level in their example):
```json
{
  "selector": {
      "$or": [
        {"director": "Lars von Trier"},
        {"year":  2003}
      ]
  },
  "sort": ["year"]
}
```
where you _must_ have indexed the `year` field, otherwise it must be `"sort": ["year:string"]"`

First 10 IDs and house addresses with list price less than or equal to 485,000 (`limit` only for example)
```json
{
	"selector": {
		"_id": {"$gt": "0"},
        "list_price": {"$lte": 485000}
	},
		"fields": [
			"_id",
			"_rev",
			"full_address",
			"list_price"
		],
		"sort": [
          {"_id": "asc"}
        ],
        "limit":  10
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
      "full_address",
      "list_price",
      "badge"
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
		"full_address": {"$regex": "4501 ARLINGTON"}
	},
	"fields": [
		"_id", "full_address"
	]
}
```

### Active listings
```json
{
	"selector": {
		"badge": {
			"$in": ["For Sale", "In Contract"]
		}
	},
	"fields": [
		"_id",
		"full_address",
		"list_price"
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
