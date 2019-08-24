
import os
import pandas as pd
import Code
from Code import score2, json_handling


def merge_data_and_scores():
    """Read in data from JSONs and scorecards, then merge as dataframe"""
    sc_path = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'scorecards.json')
    scores = json_handling.read_dicts_from_json(sc_path)
    df_scores = score2.score_dict_list_to_dataframe(scores)
    # Create MultiIndex for scores
    iterables = [['scores'], list(df_scores.columns)]
    mux = pd.MultiIndex.from_product(iterables, names=['first', 'second'])
    df_scores.columns = mux

    df_data = json_handling.all_files_to_dataframe(Code.LISTINGS_GLOB).T

    # Merge on indices
    merged = pd.merge(df_data, df_scores, left_index=True, right_index=True)
    # Drop the top level of the column multiindex (Excel tables don't like it)
    merged = merged.droplevel(level=0, axis=1)
    # Name the index
    merged.index.name = 'MLS Number'

    # Write to file
    outpath = os.path.join(Code.PROJ_PATH, 'Data', 'Processed', 'master_list.csv')
    merged.to_csv(outpath)

if __name__ == '__main__':
    merge_data_and_scores()