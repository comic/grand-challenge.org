import json
from csv import DictReader

from sklearn.metrics import accuracy_score

def get_classes(csvfile: str):
    output = []
    with open(csvfile, 'r') as f:
        reader = DictReader(f)
        for row in reader:
            output.append(row['class'])
    return output

def write_metrics(metrics: dict):
    with open('/output/metrics.json', 'w') as f:
        f.write(json.dumps(metrics, ensure_ascii=True, allow_nan=False))

if __name__ == '__main__':

    # TODO
    # We need to define how the container will be launched (ie. write out the
    # concrete commands). Allow different filenames etc?

    # Requirement: The ground truth must be part of the container
    gt = get_classes('ground_truth.csv')

    # The challenge organizer is free to define the input from the participants
    # What the user uploads will be placed directly in /input/, but the admin
    # is free to determine the file type. The only limitation is that this will
    # be a single file.
    preds = get_classes('/input/submission.csv')

    # The evaluation algorithm computes the scores of this submission
    acc = accuracy_score(gt, preds)

    # A dictionary is created of the metrics, which is then written to
    # /output/metrics.json
    metrics = {'acc': acc}
    write_metrics(metrics)
