import sys
from pathlib import Path


class ValidationError(Exception):
    pass


def run(biom_file_path):
    # Import non-buildins locally
    import biom
    import h5py

    try:
        hdf5_file = h5py.File(biom_file_path, "r")
    except OSError:
        raise ValidationError(
            "Only BIOM in valid HDF5 binary file format are supported"
        )

    # Attempt to parse it as a BIOM table
    try:
        biom.Table.from_hdf5(hdf5_file)
    except Exception:
        raise ValidationError("Does not appear to be a BIOM-format file")


def _get_file_path():
    if len(sys.argv) == 2:
        biom_file_path = Path(sys.argv[1])
        if not biom_file_path.is_file():
            print(biom_file_path, biom_file_path.exists(), file=sys.stderr)
            raise RuntimeError(
                f"Provided BIOM file path is not an existing file: {biom_file_path}"
            )
        return biom_file_path
    else:
        raise RuntimeError(
            "Incorrect number of arguments, provide (only) the BIOM file path"
        )


if __name__ == "__main__":
    run(_get_file_path())
else:
    RuntimeError("Script use only: should not be imported")
