import json
from pathlib import Path
from shutil import copy
from warnings import warn

if __name__ == "__main__":
    res = {}
    files = {x for x in Path("/input").rglob("*") if x.is_file()}

    for file in files:
        try:
            with open(file) as f:
                val = json.loads(f.read())
        except Exception as e:
            warn(f"Could not load {file} as json, {e}")
            val = "file"

        res[str(file.absolute()).replace("/input/", "")] = val

        copy(file, Path("/output/") / file.relative_to("/input/"))

    with open("/output/results.json", "w") as f:
        res = json.dumps(res, ensure_ascii=True, indent=2)
        f.write(res)
