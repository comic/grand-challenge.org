def accuracy_score(y_true, y_pred):
    if len(y_true) != len(y_pred):
        raise ValueError("Length of ground truth and prediction must match")

    score = sum(g == t for g, t in zip(y_true, y_pred))
    # Normalize
    score /= len(y_true)

    return score
