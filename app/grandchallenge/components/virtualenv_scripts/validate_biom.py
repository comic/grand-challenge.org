"""
Script that validates BIOM files by passing them through a parser.
Provide the BIOM file as an argument to the script.

If the file is valid, the script will exit cleanly (0).
Raises a ValidationScriptError if the BIOM file is not valid.



The rational for having a separate script and virtual environment is to provide
isolation of web-app and modality-specific libraries.

In the case of BIOM the clashing HDF5 libraries of the libvips library (used in panimg)
and those of h5py would lead to imports crashing when not using an virtual environment.
"""

import sys
from pathlib import Path

import biom
import h5py


class ValidationScriptError(Exception):
    pass


def run():
    biom_file_path = _get_file_path()

    try:
        hdf5_file = h5py.File(biom_file_path, "r")
    except OSError:
        raise ValidationScriptError(
            "Only BIOM in valid HDF5 binary file format are supported"
        )

    # Attempt to parse it as a BIOM table
    try:
        biom.Table.from_hdf5(hdf5_file)
    except Exception:
        raise ValidationScriptError("Does not appear to be a BIOM-format file")

    return 0


def _get_file_path():
    if len(sys.argv) == 2:
        biom_file_path = Path(sys.argv[1])
        if not biom_file_path.is_file():
            raise RuntimeError(
                f"Provided BIOM file path is not an existing file: {biom_file_path}"
            )
        return biom_file_path
    else:
        raise RuntimeError(
            "Incorrect number of arguments, provide (only) the BIOM file path"
        )


if __name__ == "__main__":
    raise SystemExit(run())
