FROM python:3.6-alpine

ENV PYTHONUNBUFFERED 1

RUN mkdir /input
RUN mkdir /output
WORKDIR /tmp

ADD ground_truth.csv /tmp
ADD evaluate_submission.py /tmp

ENTRYPOINT ["python", "evaluate_submission.py"]
