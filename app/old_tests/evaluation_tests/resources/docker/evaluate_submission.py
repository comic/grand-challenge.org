import json
from csv import DictReader


def get_classes(csvfile: str):
    output = []
    with open(csvfile, "r") as f:
        reader = DictReader(f)
        for row in reader:
            output.append(float(row["Class"]))
    return output


def write_metrics(metrics: dict):
    with open("/output/metrics.json", "w") as f:
        f.write(json.dumps(metrics, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    # Requirement: The ground truth must be part of the container
    gt = get_classes("ground_truth.csv")
    # The challenge organizer is free to define the input from the participants
    # What the user uploads will be placed directly in /input/, but the admin
    # is free to determine the file type. The only limitation is that this will
    # be a single file.
    preds = get_classes("/input/submission.csv")
    # The evaluation algorithm computes the scores of this submission
    acc = sum([a == b for a, b in zip(gt, preds)]) / len(gt)
    # A dictionary is created of the metrics, which is then written to
    # /output/metrics.json
    metrics = {"acc": acc, "inf": float("inf"), "nan": float("nan")}
    write_metrics(metrics)
