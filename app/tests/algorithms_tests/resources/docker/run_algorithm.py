import json
import os
import shutil
from warnings import warn


def write_results(path: str, res: dict):
    with open(path, "w") as f:
        f.write(json.dumps(res, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    # The algorithm owner is free to define the input from the participants
    # What the user uploads will be placed directly in /input/, but the admin
    # is free to determine the file type. The only limitation is that this will
    # be a single file.
    input_file = "/input/input_file.tif"
    os.makedirs("/output/images")
    shutil.copyfile(input_file, "/output/images/output.tif")

    # A dictionary is created for the results, which is then written to
    # /output/results.json
    results = {
        "entity": "out.tif",
        "metrics": {"abnormal": 0.19, "normal": 0.81},
    }
    write_results("/output/results.json", results)

    detection_results = {
        "detected points": [
            {"type": "Point", "start": [0, 1, 2], "end": [0, 1, 2]}
        ]
    }
    write_results("/output/detection_results.json", detection_results)
    # stdout should be saved
    print("Greetings from stdout")
    # so should stderr
    warn("Hello from stderr")
