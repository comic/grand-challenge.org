import json
from pathlib import Path
from shutil import copy
from warnings import warn

if __name__ == "__main__":
    res = {"score": 1}  # dummy metric for ranking on leaderboard
    files = {x for x in Path("/input").rglob("*") if x.is_file()}

    for file in files:
        try:
            with open(file) as f:
                val = json.loads(f.read())
        except Exception as e:
            warn(f"Could not load {file} as json, {e}")
            val = "file"

        res[str(file.absolute())] = val

        # Copy all the input files to output
        new_file = Path("/output/") / file.relative_to("/input/")
        new_file.parent.mkdir(parents=True, exist_ok=True)
        copy(file, new_file)

    for output_filename in ["results", "metrics"]:
        with open(f"/output/{output_filename}.json", "w") as f:
            f.write(json.dumps(res))
