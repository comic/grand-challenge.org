import json
from pathlib import Path

if __name__ == "__main__":
    res = {
        "inputs": [
            str(x).replace("/input/", "")
            for x in Path("/input").rglob("*")
            if not x.is_dir()
        ]
    }
    with open("/output/results.json", "w") as f:
        res = json.dumps(res, ensure_ascii=True, indent=2)
        f.write(res)
