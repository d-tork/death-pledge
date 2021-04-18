"""Predict a sale price based on historic data."""
import pandas as pd
import numpy as np
import logging
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn import metrics

from deathpledge.post import feature


class SalePricePredictor(object):
    cols = [
        'mls_number', 'full_address',
        'list_price', 'new_on_homescout', 'status',
        'beds', 'baths', 'full_bathrooms', 'sqft', 'basement',
        'structure_type', 'architectural_style', 'year_built', 'levels_count', 'new_construction',
        'acres', 'fireplaces', 'air_conditioning', 'garage_capacity', 'has_laundry',
        'has_common_walls',
        'county', 'PlaceName', 'StateName', 'ZipCode',
        'hoa_fee', 'has_hoa', 'county_tax', 'condocoop_fee', 'city_tax', 'total_taxes',
        'commute_time', 'first_leg', 'first_walk', 'tether',
        'sold', 'sale_price', 'estimated_value',
    ]

    def __init__(self, df: pd.DataFrame):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self.df = df
        self.sold = self._get_sold_homes(df)
        self.lr = LinearRegression()
        self.feature_cols = (FeatureColumns.categorical
                             + FeatureColumns.numerical
                             + FeatureColumns.boolean)
        self.column_transformer = ColumnTransformer(
            [('categoricals', OneHotEncoder(handle_unknown='ignore'), FeatureColumns.categorical),
             ('continuous', StandardScaler(), FeatureColumns.numerical)],
            remainder='passthrough')

    @staticmethod
    def _get_sold_homes(df):
        return df.loc[df['sold'].notna()].copy()

    def model_sale_price(self):
        self._drop_null_rows_and_cols(self.sold)
        X_train, X_test, y_train, y_test = self._split_data()
        X_train_tx, X_test_tx = self._transform_X_features(X_train, X_test)
        self.lr.fit(X_train_tx, y_train)
        lr_score = self.lr.score(X_test_tx, y_test)
        self.logger.info(f'LinReg score: {lr_score:.3f}')
        print(f'LinReg score: {lr_score:.3f}')

    @staticmethod
    def _drop_null_rows_and_cols(df):
        df.dropna(axis=0, inplace=True, subset=['first_leg', 'commute_time', 'first_walk'])
        df.dropna(axis=1, inplace=True)

    def _split_data(self):
        target_col = ['sale_price']
        X = self.sold[self.feature_cols]
        y = self.sold[target_col]
        return train_test_split(X, y)

    def _transform_X_features(self, X_train, X_test):
        X_train_transformed = self.column_transformer.fit_transform(X_train)
        X_test_transformed = self.column_transformer.transform(X_test)
        return X_train_transformed, X_test_transformed

    def predict_for_active(self) -> pd.DataFrame:
        for_sale = self.df.loc[self.df.status.str.lower().str.contains('active')].copy()
        self._drop_null_rows_and_cols(for_sale)
        X_for_sale = for_sale[self.feature_cols]
        X_for_sale_transformed = self.column_transformer.transform(X_for_sale)
        for_sale_pred = self.lr.predict(X_for_sale_transformed)
        predictions = pd.Series(list(for_sale_pred)).apply(pd.Series)  # TODO: rename here?
        final = for_sale.reset_index(drop=True).join(predictions)
        final.rename(columns={0: 'predicted_price'}, inplace=True)
        return final


class FeatureColumns(object):
    categorical = ['structure_type',
                   'architectural_style',
                   'county',
                   'ZipCode',
                   'StateName',
                   'first_leg']
    numerical = ['beds',
                 'baths',
                 'sqft',
                 'year_built',
                 'commute_time',
                 'first_walk',
                 'tether',
                 'fireplaces',
                 'garage_capacity',
                 'days_on_market',
                 'county_tax',
                 'city_tax',
                 'levels_count']
    boolean = ['has_hoa',
               'basement',
               'air_conditioning',
               'has_common_walls',
               'has_laundry']


def sample():
    df = feature.sample()
    sale_price = SalePricePredictor(df)
    sale_price.model_sale_price()
    active_predicted = sale_price.predict_for_active()
    print(active_predicted.head())


if __name__ == '__main__':
    sample()
