import json
import os


if __name__ == "__main__":
    res = {"inputs": os.listdir("/input")}
    with open("/output/results.json", "w") as f:
        res = json.dumps(res, ensure_ascii=True, indent=2)
        f.write(res)
