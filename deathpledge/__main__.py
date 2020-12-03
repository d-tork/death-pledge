"""Run actions on housing search spreadsheet."""
from os import path
import argparse

import deathpledge
from deathpledge.logs.log_setup import setup_logging
from deathpledge.logs import *
from deathpledge.api_calls import google_sheets as gs
from deathpledge import classes, scrape2, support, database


@support.timing
def main():
    logging_config = path.join(deathpledge.PROJ_PATH, 'config', 'logging.yaml')
    setup_logging(config_path=logging_config)

    args = parse_commandline_arguments()
    google_creds = gs.get_creds()

    get_raw_data(args, google_creds)
    process_data(args, google_creds)
    return


def parse_commandline_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', default=None, type=int, dest='last_n')
    return parser.parse_args()


def get_raw_data(args, google_creds):
    urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    scrape2.scrape_from_url_df(urls, force_all=False, quiet=True)
    gs.refresh_url_sheet(google_creds)


def process_data(args, google_creds):
    new_urls = gs.get_url_dataframe(google_creds, last_n=args.last_n)
    fetched_raw_docs = database.get_bulk_docs(
        db_name=deathpledge.RAW_DATABASE_NAME,
        doc_ids=new_urls.df['docid'].tolist()
    )
    for row in new_urls.itertuples():
        doc = next((d for d in fetched_raw_docs if d['id'] == row.docid))['doc']
        home = classes.Home(
            url=doc['url'],
            added_date=doc['added_date'],
            docid=doc['_id']
        )
        home.update(doc)
        home.clean()
        home.enrich()
        home.upload(db_name=deathpledge.DATABASE_NAME)


if __name__ == '__main__':
    main()
