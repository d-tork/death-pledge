"""Apply cleaning for analysis and join of the sources."""
import pandas as pd
import numpy as np
import logging
import os

from deathpledge import PROJ_PATH
from deathpledge.post import fetch

logger = logging.getLogger(__name__)


class HomeData(object):
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def run_all_cleaning(self):
        self.address_cloudant_issues()
        self.address_realscout_homescout_join()
        self.apply_transformations()
        self.handle_outliers()

    def address_cloudant_issues(self):
        self._drop_unwanted_cols()

    def _drop_unwanted_cols(self):
        cols = ['_id', '_rev', 'index', 'name', 'type', 'ddoc', 'views', 'indexes', 'language']
        self.df.drop(columns=cols, errors='ignore', inplace=True)

    def address_realscout_homescout_join(self):
        self._fill_has_hoa()
        self._fill_new_construction()
        self._fill_estimated_value()
        self._yes_no_to_boolean()
        self._calculate_levels_count()

    def _fill_has_hoa(self):
        """Realscout had it, Homescout needs it"""
        df = self.df.copy()
        yes_if_hoa_fee = df['hoa_fee'].notna().map(lambda x: 1 if x else None)
        yes_if_condo_fee = df['condocoop_fee'].notna().map(lambda x: 1 if x else None)
        df['has_hoa'] = yes_if_hoa_fee.fillna(yes_if_condo_fee).fillna(0).astype('int32')
        self.df = df

    def _fill_new_construction(self):
        """new_construction doesn't exist in RS, but it does going forward

        Ys and Ns will be converted to 1/0 later
        """
        self.df['new_construction'].fillna('N', inplace=True)

    def _fill_estimated_value(self):
        """RS didn't have estimates, so just fill it with list price"""
        self.df['estimated_value'].fillna(self.df['list_price'], inplace=True)

    def _fill_additional_laundry(self):
        """Some listings mention laundry in description, but not in laundry field."""
        laundry_in_desc = self.df['description'].str.lower().str.contains('laundry')
        laundry_in_appliances = self.df['appliances'].apply(self._eval_appliances_for_laundry)
        any_laundry = (laundry_in_desc | laundry_in_appliances)
        self.df['laundry'].fillna(any_laundry, inplace=True)

    @staticmethod
    def _eval_appliances_for_laundry(s: str) -> bool:
        """Look for laundry-related terms in the appliances string."""
        try:
            appliance_list = eval(s)
        except TypeError:
            return False
        else:
            if 'washer' in [x.lower() for x in appliance_list]:
                return True
            elif any([x for x in appliance_list if 'dryer' in x.lower()]):
                return True
            else:
                return False

    def _yes_no_to_boolean(self):
        # TODO: this should come later, some of these may be gone or renamed
        yesno_cols = ['water_access', 'basement', 'air_conditioning', 'new_construction']
        for col in yesno_cols:
            self.df[col] = self.df[col].map({'Yes': 1, 'Y': 1, 'No': 0, 'N': 0}).fillna(0)
            self.df[col] = self.df[col].astype('int32')

    def _calculate_levels_count(self):
        story_count = self.df['story_list'].fillna('').map(lambda x: len(x.split(',')))
        self.df['levels_count'] = story_count
        self.df['levels_count'] = self.df['levels_count'].map(lambda x: str(x).replace('+', ''))
        self.df['levels_count'] = pd.to_numeric(self.df['levels_count'], errors='coerce').fillna(1)

    def apply_transformations(self):
        self._str_col_yes_if_something()
        self._add_exploded_fields('parsed_address')
        zero_for_null_cols = ['garage_capacity', 'fireplaces', 'city_tax']
        self._fill_zero_for_null(zero_for_null_cols)
        drop_cols = ['total_garage_and_parking_spaces', 'StreetNamePostDirectional', 'StreetNamePreType',
                     'StreetNamePreDirectional', 'OccupancyIdentifier', 'StreetNamePostType',
                     'green_information', 'waterfront_features', 'water_body_type', 'body_of_water_information',
                     'zoning', 'total_rooms', 'road_frontage', 'directions', 'virtual_tour_url',
                     'building_sites']
        self.df.drop(columns=drop_cols, errors='ignore', inplace=True)
        self._parse_currency_fields()
        self._downcast_floats_to_int()
        self._convert_yn_cols_to_bool(['garage'])

    def _str_col_yes_if_something(self):
        str_cols_for_bool = """common_walls heating cooling laundry""".split()
        for col in str_cols_for_bool:
            new_colname = f'has_{col}'
            s = self.df[col].fillna('')
            self.df[new_colname] = s.map(lambda x: 1 if len(str(x)) > 0 else 0)

    def _add_exploded_fields(self, col):
        df = self.df.copy()
        df = df.reset_index().join(self._explode_list_series(df[col]), sort=True)
        df.drop(columns=[col], inplace=True)
        self.df = df

    @staticmethod
    def _explode_list_series(s):
        list_from_s = [eval(x) for x in s]
        df = pd.DataFrame(list_from_s)
        return df

    def _fill_zero_for_null(self, cols):
        for col in cols:
            self.df[col].fillna(0, inplace=True)

    def _parse_currency_fields(self):
        """county_tax sometimes has currency symbols"""
        for col in ['county_tax', 'city_tax', 'total_taxes', 'estimated_value']:
            self.df[col] = self.df[col].map(str).str.replace('$', '')
            self.df[col] = self.df[col].map(str).str.replace(',', '')
            self.df[col].fillna(0, inplace=True)

    def _downcast_floats_to_int(self):
        for col in self.df:
            try:
                self.df[col] = pd.to_numeric(self.df[col], downcast='integer')
            except (ValueError, TypeError):
                continue

    def _convert_yn_cols_to_bool(self, cols):
        for col in cols:
            try:
                self.df[col] = self._map_yn_to_int(self.df[col])
                self.df[col] = self.df[col].fillna(0)
            except AttributeError:
                continue

    @staticmethod
    def _map_yn_to_int(s: pd.Series):
        return np.where(s.str.contains('No'), 0, 1)

    def handle_outliers(self):
        self._fix_garage_capacity_outliers()
        self._fix_tax_outliers('city_tax', 'total_taxes')
        self._fix_zero_sqft()

    def _fix_garage_capacity_outliers(self):
        """Garage capacity for a couple homes is insane (the parking garage spaces)"""
        max_reasonable_capacity = 5
        col = 'garage_capacity'
        outliers = self.df[col].loc[self.df[col] > max_reasonable_capacity].tolist()
        self.df[col].replace(to_replace=outliers, value=1, inplace=True)

    def _fix_tax_outliers(self, *cols):
        """Some homes use the tax estimated value for city tax amount."""
        for col in cols:
            q1, q3 = np.percentile(self.df[col], [25, 75])
            iqr = q3 - q1
            lower_range = max(q1 - (1.5 * iqr), 0)
            upper_range = q3 + (1.5 * iqr)
            min_outliers = self.df[col].loc[self.df[col] < lower_range].tolist()
            max_outliers = self.df[col].loc[self.df[col] > upper_range].tolist()
            self.df[col].replace(min_outliers, lower_range, inplace=True)
            self.df[col].replace(max_outliers, upper_range, inplace=True)

    def _fix_zero_sqft(self):
        """Some homes have 0 sqft, so use the median."""
        col = 'sqft'
        median_value = self.df[col].median()
        outliers = self.df[col].loc[self.df[col] == 0].tolist()
        self.df[col].replace(outliers, median_value, inplace=True)


def sample():
    # docs = fetch.get_homes_from_cloudant()
    # df = fetch.get_dataframe_from_docs(docs)
    raw_data_file = os.path.join(PROJ_PATH, 'data', '01-raw.csv')
    df = pd.read_csv(raw_data_file, index_col=None)
    home_data = HomeData(df)
    home_data.run_all_cleaning()
    logger.debug('break point here')
    return home_data


if __name__ == '__main__':
    sample()
