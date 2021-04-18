"""Post-processing

This module handles the data analysis portion, executed not on each
home listing but on all listings in bulk.

"""

from deathpledge.post import fetch, clean, feature, predict, score

__all__ = [
    'fetch',
    'clean',
    'feature',
    'predict',
    'score'
]
