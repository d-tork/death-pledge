"""
Makes custom handlers for logging available if this package (deathpledge.logs) is imported as

>>>from deathpledge.logs import *

The two handlers will now be in the __main__ namespace, and referenced properly from the
YAML config file.
"""
from .log_setup import dp_infologger, dp_debugger

__all__ = [
    'dp_infologger', 'dp_debugger'
]
