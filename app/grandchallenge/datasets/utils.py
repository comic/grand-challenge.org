# -*- coding: utf-8 -*-
import csv
import itertools
from codecs import iterdecode


def lower_first(iterator):
    """ Lowers the first line of a file """
    return itertools.chain([next(iterator).lower()], iterator)


def process_csv_file(filehandle):
    """ Reads a csv file into records, requires open file handle """
    reader = csv.DictReader(
        lower_first(iterdecode(filehandle, encoding="utf-8")),
        skipinitialspace=True,
    )
    return [row for row in reader]
