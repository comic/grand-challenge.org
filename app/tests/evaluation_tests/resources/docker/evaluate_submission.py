import json
from csv import DictReader
from pathlib import Path
from warnings import warn


def get_classes(csvfile: Path):
    output = []
    with open(csvfile) as f:
        reader = DictReader(f)
        for row in reader:
            output.append(float(row["Class"]))
    return output


def write_metrics(metrics: dict):
    with open("/output/metrics.json", "w") as f:
        f.write(json.dumps(metrics, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    # Requirement: The ground truth must be part of the container
    gt = get_classes(Path("ground_truth.csv"))
    # The challenge organizer is free to define the input from the participants
    # What the user uploads will be placed directly in /input/, but the admin
    # is free to determine the file type. The only limitation is that this will
    # be a single file.
    input_file = next(Path("/input/").glob("*.csv"))
    preds = get_classes(input_file)
    # The evaluation algorithm computes the scores of this submission
    acc = sum([a == b for a, b in zip(gt, preds)]) / len(gt)
    # A dictionary is created of the metrics, which is then written to
    # /output/metrics.json
    metrics = {"acc": acc, "inf": float("inf"), "nan": float("nan")}
    write_metrics(metrics)
    # stdout should be saved
    print("Greetings from stdout")
    # so should stderr
    warn("Hello from stderr")
