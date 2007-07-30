# Imports
import re

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    return formatter.rawHTML('&hearts;')
