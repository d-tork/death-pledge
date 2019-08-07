import os
import pandas as pd
import numpy as np
from Code import PROJ_PATH


def read_and_prep_data(filename):

    data = os.path.join(PROJ_PATH, 'Data', 'Processed', filename)
    df = pd.read_csv(data, index_col=0)

    # Transpose and convert Yes/No to integers
    df = df.T
    df.replace('Yes', 1, inplace=True)
    df.replace('No', 0, inplace=True)
    return df


def calc_score_for_column(df, df_scores, col):
    print('Column count: {}'.format(len(df.columns)))

    # Convert all to float32 in order to merge
    # Fields that are categorical/object will need to be run through a converter separately
    # (just like how I converted all Yes=1 and No=0)
    # score_col = '{}_score'.format(col)
    col_loc = df_scores.columns.get_loc(col)
    score_col = df_scores.columns[col_loc + 1]

    print('{} to {}'.format(col, score_col))
    df[col] = pd.to_numeric(df[col], downcast='float')
    df_scores[col] = pd.to_numeric(df_scores[col], downcast='float')
    df_scores[score_col] = pd.to_numeric(df_scores[score_col], downcast='float')

    # Clean up dataframes for merging
    df.sort_values(col, inplace=True)
    df.fillna(0, inplace=True)
    df_right = df_scores[[col, score_col]].dropna()

    return pd.merge_asof(df, df_right, on=col)



def laundry_in_appliances(df):
    s1 = (df['Appliances'].str.contains('Washer')) & (df['Appliances'].str.contains('Dryer'))
    s1.name = 'has_laundry'
    df[s1.name] = s1.astype(int)
    return df


def rate_structure_type(df):

    def fill_structure_score(full_str, struc_dict):
        for word, score in struc_dict.items():
            if word in full_str:
                return struc_dict[word]
            else:
                continue
    s_fullstr = df['Structure Type']
    struc_scores_dict = {'Detached': 3,
                         'Townhouse': 2,
                         'Unit': 1}
    df['structure_type_score'] = s_fullstr.apply(fill_structure_score, args=(struc_scores_dict,))
    return df


if __name__ == '__main__':
    df_data = read_and_prep_data('scraped_results.csv')

    # Read in my score lookup worksheet
    scores_filepath = os.path.join(PROJ_PATH, 'Code', 'scores.csv')
    scores = pd.read_csv(scores_filepath)

    score_calc_list = [x for x in scores.columns if '_score' not in x]

    df_scored = df_data.copy()
    for col in score_calc_list:
        # Regular scoring
        df_scored = calc_score_for_column(df_scored, scores, col)

    # Special scoring
    # Price per SQFT and relative price scores are dynamic, based on the quartiles
    df_data['Price Per SQFT'] = pd.to_numeric(df_data['Price Per SQFT'], downcast='float')
    price_sqft_dict = {'Price Per SQFT': [0,
                                          df_data['Price Per SQFT'].quantile(.25),
                                          df_data['Price Per SQFT'].median(),
                                          df_data['Price Per SQFT'].max()],
                       'price_sqft_score': [3, 2, 1, 0.5]}
    df_data['price'] = pd.to_numeric(df_data['price'], downcast='float')
    relative_price_dict = {'price': [df_data['price'].min(),
                                     df_data['price'].quantile(.25),
                                     df_data['price'].median(),
                                     df_data['price'].quantile(.75),
                                     df_data['price'].max()],
                           'price_relative_score': [3.5, 3, 2, 1, 0]}  # Why is it mapping these backwards??

    for score_dict in [price_sqft_dict, relative_price_dict]:
        df_score_lookup = pd.DataFrame({k: pd.Series(v) for k, v in score_dict.items()}, dtype=np.float32)
        original_col = list(score_dict.keys())[0] # Taking a chance that this always returns the first one
        df_scored = calc_score_for_column(df_scored, df_score_lookup, original_col)

    laundry_in_appliances(df_scored)
    rate_structure_type(df_scored)

    # Commute time
    df_scored['cm_time'].replace(0, np.nan, inplace=True)
    df_scored['cm_time'] = pd.to_timedelta(df_scored['cm_time'])
    df_scored['commute_score'] = (df_scored['cm_time']*-1).rank(method='min')

    # Calculate total points
    score_col_list = [x for x in df_scored.columns if '_score' in x]
    df_scored['total_score'] = df_scored[score_col_list].sum(axis=1)
    output_filepath = os.path.join(PROJ_PATH, 'Data', 'Processed', 'df_scored.csv')
    df_scored.to_csv(output_filepath)

