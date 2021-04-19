"""Predict a sale price based on historic data."""
import pandas as pd
import numpy as np
import logging
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn import metrics
from xgboost import XGBRegressor
from os import path
import pickle

import deathpledge
from deathpledge.post import feature


class SalePricePredictor(object):
    def __init__(self, df: pd.DataFrame):
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')
        self.df = df
        self.sold = self._prepare_modeling_dataset()
        self.lr = LinearRegression()
        self.feature_cols = (FeatureColumns.categorical
                             + FeatureColumns.numerical
                             + FeatureColumns.boolean)
        self.column_transformer = ColumnTransformer(
            [('categoricals', OneHotEncoder(handle_unknown='ignore'), FeatureColumns.categorical),
             ('continuous', StandardScaler(), FeatureColumns.numerical)],
            remainder='passthrough')
        self.X_train, self.X_test, self.y_train, self.y_test = None, None, None, None

    def _prepare_modeling_dataset(self) -> pd.DataFrame:
        """Filter for labeled rows (sold homes) and drop all irrelevant nulls."""
        sold = self.df.loc[self.df['sold'].notna()].copy()
        self._drop_null_rows_and_cols(sold)
        self._downcast_all_numeric_cols(sold)
        return sold

    def _drop_null_rows_and_cols(self, df: pd.DataFrame):
        df.dropna(axis=0, how='any', inplace=True, subset=['first_leg', 'commute_time', 'first_walk'])
        cols_before = set(df.columns)
        df.dropna(axis=1, how='any', inplace=True)
        cols_after = set(df.columns)
        cols_dropped = cols_before - cols_after
        self.logger.info(f'Columns dropped for having null values:\t\n{cols_dropped}')

    @staticmethod
    def _downcast_all_numeric_cols(df):
        for col in df:
            df[col] = pd.to_numeric(df[col], downcast='integer', errors='ignore')

    def model_sale_price(self):
        self.X_train, self.X_test, self.y_train, self.y_test = self._split_data()
        X_train_tx, X_test_tx = self._transform_X_features()
        self.lr.fit(X_train_tx, self.y_train)
        self.score_model(X_test_tx)

    def model_with_xgboost(self):
        X_train_tx, X_test_tx = self._transform_X_features()
        xg_model = XGBRegressor(random_state=0)
        parameters = {
            'n_estimators': [100, 120, 150, 200],
            'learning_rate': [0.02, 0.05, 0.07]
        }
        search = GridSearchCV(estimator=xg_model, param_grid=parameters, cv=3)
        search.fit(X_train_tx, self.y_train)
        print('-' * 25)
        print(f'Best parameters {search.best_params_}')
        print(
            f'Mean cross-validated accuracy score of the best_estimator: ',
            f'{search.best_score_:.3f}'
        )
        print('-' * 25)
        print(f'XGBoost train score: {search.score(X_train_tx, self.y_train)}')
        print(f'XGBoost test score: {search.score(X_test_tx, self.y_test)}')
        y_pred = search.predict(X_test_tx)
        print('Mean absolute error: ', metrics.mean_absolute_error(self.y_test, y_pred))
        return search

    def _split_data(self):
        target_col = ['sale_price']
        X = self.sold[self.feature_cols]
        y = self.sold[target_col]
        return train_test_split(X, y, train_size=0.8, random_state=72)

    def _transform_X_features(self):
        X_train_transformed = self.column_transformer.fit_transform(self.X_train)
        X_test_transformed = self.column_transformer.transform(self.X_test)
        return X_train_transformed, X_test_transformed

    def score_model(self, x_test_transform):
        """Print statistics regarding model performance."""
        model_score = self.lr.score(x_test_transform, self.y_test)
        print(f'Model score: {model_score:.4}')

        # Baselines
        y_list_price = self.sold.loc[self.X_test.index, 'list_price']
        list_price_score = self.lr.score(x_test_transform, y_list_price)
        print(f'Using list price to predict: {list_price_score:.4}')

        y_estimate = self.sold.loc[self.X_test.index, 'estimated_value']
        estimate_score = self.lr.score(x_test_transform, y_estimate)
        print(f'Using homescout estimated value: {estimate_score:.4}')

        # Metrics
        y_pred = self.lr.predict(x_test_transform)
        print(f'Mean Absolute Error (MAE): {metrics.mean_absolute_error(self.y_test, y_pred):.4}')
        print(f'Mean Squared Error (MSE): {metrics.mean_squared_error(self.y_test, y_pred):.4}')
        print(f'Root Mean Squared Error (RMSE): {np.sqrt(metrics.mean_squared_error(self.y_test, y_pred))}')

    def predict_for_active(self, estimator) -> pd.DataFrame:
        for_sale = self.df.loc[self.df.status.str.lower().str.contains('active')].copy()
        self._drop_null_rows_and_cols(for_sale)
        X_for_sale = for_sale[self.feature_cols]
        X_for_sale_transformed = self.column_transformer.transform(X_for_sale)
        for_sale_pred = estimator.predict(X_for_sale_transformed)
        predictions = pd.Series(list(for_sale_pred)).apply(pd.Series)
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
                 'levels_count',
                 'price_sqft']
    boolean = ['has_hoa',
               'basement',
               'air_conditioning',
               'has_common_walls',
               'pool_description',
               'has_laundry']


def sample():
    df = feature.sample(online=False)
    print(df.shape)
    sale_price = SalePricePredictor(df)
    sale_price.model_sale_price()
    xgb_model = sale_price.model_with_xgboost()
    active_predicted = sale_price.predict_for_active(estimator=xgb_model)
    print(active_predicted[['mls_number', 'list_price', 'predicted_price']].head())
    outfile = path.join(deathpledge.PROJ_PATH, 'data', '04-predicted.csv')
    active_predicted.to_csv(outfile, index=False)


if __name__ == '__main__':
    sample()
