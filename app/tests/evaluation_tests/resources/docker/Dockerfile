FROM python:3.11-alpine

WORKDIR /tmp

RUN addgroup -S app && adduser -S -G app app
USER app

ADD ground_truth.csv /tmp
ADD evaluate_submission.py /tmp

ENTRYPOINT ["python", "evaluate_submission.py"]
