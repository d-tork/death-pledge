"""Fetch listing data from Cloudant for all homes."""

import pandas as pd
from cloudant.result import QueryResult
from cloudant.query import Query
import logging
from os import path

import deathpledge
from deathpledge import database as db

logger = logging.getLogger(__name__)


def get_homes_from_cloudant() -> list:
    """Get all homes.

    Returns:
        List of docs as dictionaries.
    """
    with db.DatabaseClient() as cloudant:
        clean_db = cloudant[deathpledge.DATABASE_NAME]
        query = Query(clean_db,
                      selector={'doctype': 'home', 'scraped_source': 'Homescout'},
                      use_index='homeIndex')
        result_collection = QueryResult(query)
    rows = db.rate_limit_pull(result_collection, est_doc_count=900)
    return rows


def get_dataframe_from_docs(docs: list) -> pd.DataFrame:
    """Convert Cloudant docs to dataframe."""
    df = pd.DataFrame(docs)
    logger.info(df['scraped_source'].value_counts())
    return df


def sample():
    rows = get_homes_from_cloudant()
    df = get_dataframe_from_docs(rows)
    print(df.head())
    print(df['scraped_source'].value_counts())
    raw_outpath = path.join(deathpledge.PROJ_PATH, 'data', '01-raw.csv')
    df.to_csv(raw_outpath, index=False)


if __name__ == '__main__':
    sample()
