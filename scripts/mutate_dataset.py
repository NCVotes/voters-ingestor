#!/usr/bin/env python3
"""mutate_dataset.py path/to/tab-delimited.txt

This script will take a tab delimited NC voter dataset and output a dataset of
the same voters with a few of the last names and addresses changed. This can
be used to generate test data that simulates importing new data with changes to
track.

The new version is printed to stdout and can be piped to a new file.

Example usage:

    scripts/mutate_dataset.py  voter/test_data/2010-10-31T00-00-00/snapshot_latin1.txt > voter/test_data/2011-10-31T00-00-00/snapshot.txt
"""

import sys
import csv
import random

path = sys.argv[1]
f = open(path)

reader = csv.DictReader(f, delimiter='\t')

LAST_NAMES = [
    'WILSON',
    'MCDONALD',
    'SMITH',
    'RODRIGUEZ',
]

STREET_NAMES = [
    'TALLOWHILL',
    'MARTIN LUTHAR KING',
    'MAIN',
    'SECOND',
    'OLD BARLEY',
]
STREET_TYPES = [
    'RD', 'ST', 'BLVD', 'AVE',
]

writer = csv.DictWriter(sys.stdout, delimiter='\t', fieldnames=reader.fieldnames)
writer.writeheader()

rows = list(reader)
for row in rows:
    mutate = random.random() > 0.7
    mutate_which = random.choice("name addr".split())

    if mutate:
        if mutate_which == "name":
            row['last_name'] = random.choice(LAST_NAMES)
        elif mutate_which == "addr":
            row['street_name'] = random.choice(STREET_NAMES)
            row['street_type_cd'] = random.choice(STREET_TYPES)
            row['zip_code'] = random.randint(10000, 99999)
    writer.writerow(row)
