# -*- coding: utf-8 -*-
import csv
import itertools
from codecs import iterdecode
from typing import Union


def lower_first(iterator):
    """ Lowers the first line of a file """
    return itertools.chain([next(iterator).lower()], iterator)


def infer_type(value: str) -> Union[str, float, int]:
    """
    Tries to convert the value to its implicit type, returns the original if
    unsuccessful
    """
    operations = [int, float]

    for op in operations:
        try:
            return op(value)
        except ValueError:
            continue

    return value


def type_values(input: dict) -> dict:
    """
    Takes a dictionary of strings and tries to convert the data to the
    intended type
    """
    return {k: infer_type(v) for k, v in input.items()}


def process_csv_file(filehandle):
    """ Reads a csv file into records, requires open file handle """
    reader = csv.DictReader(
        lower_first(iterdecode(filehandle, encoding="utf-8")),
        skipinitialspace=True,
    )
    return [type_values(row) for row in reader]
