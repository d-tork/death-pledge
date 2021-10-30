"""Engineer features for analysis."""
import pandas as pd
import numpy as np
from os import path

import deathpledge
from deathpledge.post import clean


def add_engineered_features(home_data: clean.HomeData):
    home_data.df = calc_days_on_market(home_data.df)
    home_data.df = calc_taxes_price_ratio(home_data.df)
    home_data.df = calc_diff_from_estimate(home_data.df)
    home_data.df = handle_nulls(home_data.df)


def calc_days_on_market(df: pd.DataFrame):
    new_on_homescout = pd.to_datetime(df['new_on_homescout'])
    dom = (pd.Timestamp.now() - new_on_homescout).dt.days
    df['days_on_market'] = dom
    return df


def calc_taxes_price_ratio(df: pd.DataFrame):
    ratio = df['total_taxes'] / df['list_price']
    df['taxes_ratio'] = ratio
    return df


def calc_diff_from_estimate(df: pd.DataFrame):
    """Higher is under-valued, lower is over-valued."""
    diff = df['estimated_value'] - df['list_price']
    diff_pct = diff / df['list_price']
    df['value_ratio'] = diff_pct
    return df


def handle_nulls(df: pd.DataFrame):
    """Null handling according to specific rules, for modeling."""
    df['county_tax'].fillna(pd.to_numeric(df['county_tax'].dropna()).mean(), inplace=True)
    df['hoa_fee'].fillna(0, inplace=True)
    df['condocoop_fee'].fillna(0, inplace=True)
    return df


def sample(**kwargs):
    home_data = clean.sample(**kwargs)
    add_engineered_features(home_data)
    print(home_data.df.head())
    outfile = path.join(deathpledge.PROJ_PATH, 'data', '03-feature.csv')
    home_data.df.to_csv(outfile, index=False)
    return home_data.df


if __name__ == '__main__':
    sample()
